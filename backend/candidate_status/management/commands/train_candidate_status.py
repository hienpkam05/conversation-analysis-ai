import json
import math
from pathlib import Path
import random

from django.core.management.base import BaseCommand, CommandError

from consultation_quality.services import InputError
from consultation_quality.training_data import digest
from candidate_status.dataset import validate_bundle
from candidate_status.metrics import CODES, probability_label, scores, select_threshold
from candidate_status.ml import FORMAT, WINDOWING, file_hash, forward_probabilities, labels_config, windows_for, write_json


class Command(BaseCommand):
    help = "Fine-tune ViDeBERTa từ bundle đã duyệt; chỉ dùng checkpoint local, không tự tải hoặc duyệt phát hành."

    def add_arguments(self, parser):
        parser.add_argument("bundle", type=Path)
        parser.add_argument("--base-model", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--license-reviewed", action="store_true")
        parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
        parser.add_argument("--epochs", type=int, default=3)
        parser.add_argument("--learning-rate", type=float, default=2e-5)
        parser.add_argument("--max-length", type=int, default=256)
        parser.add_argument("--max-windows", type=int, default=16)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        try:
            self.train(options)
        except (InputError, OSError, ValueError, ImportError, RuntimeError) as exc:
            raise CommandError(f"Chưa huấn luyện được: {exc}") from exc

    def train(self, options):
        bundle = json.loads(options["bundle"].read_text(encoding="utf-8"))
        splits = validate_bundle(bundle)
        if any(not any(row["label"] == code for row in splits["train"]) for code in CODES):
            raise InputError("Tập train chưa có đủ 5 trạng thái và unknown; bổ sung nhãn, không thay bằng nhãn giả.")
        output, base = options["output"], options["base_model"]
        if output.exists() or not base.is_dir() or not options["license_reviewed"]:
            raise InputError("Cần checkpoint local, xác nhận giấy phép và thư mục output mới.")
        length, limit = options["max_length"], options["max_windows"]
        if not 32 <= length <= 512 or not 1 <= limit <= 32 or not 1 <= options["epochs"] <= 30 or not math.isfinite(options["learning_rate"]) or not 0 < options["learning_rate"] <= .001:
            raise InputError("Tham số train vượt giới hạn hỗ trợ.")
        try:
            import torch
            from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer
        except ImportError:
            raise InputError("Môi trường train thiếu torch/transformers/safetensors; xem TRAINING.md, không cài vào web tự động.") from None
        random.seed(options["seed"])
        torch.manual_seed(options["seed"])
        if options["device"] == "cuda" and not torch.cuda.is_available():
            raise InputError("CUDA chưa sẵn sàng trong môi trường train.")
        config = AutoConfig.from_pretrained(str(base), local_files_only=True, trust_remote_code=False)
        if config.model_type != "deberta-v2" or length > config.max_position_embeddings:
            raise InputError("Checkpoint không phải họ ViDeBERTa/DeBERTa-v2 tương thích hoặc max-length quá lớn.")
        tokenizer = AutoTokenizer.from_pretrained(str(base), local_files_only=True, trust_remote_code=False, use_fast=True)
        # Validate every conversation before allocating model/training; never silently truncate a holdout.
        for rows in splits.values():
            for row in rows:
                windows_for(tokenizer, row["utterances"], length, limit)
        model = AutoModelForSequenceClassification.from_pretrained(str(base), local_files_only=True,
            trust_remote_code=False, num_labels=len(CODES), ignore_mismatched_sizes=True,
            weights_only=True, **labels_config()).to(options["device"])
        model.gradient_checkpointing_enable()
        optimizer = torch.optim.AdamW(model.parameters(), lr=options["learning_rate"])

        def predict(rows):
            model.eval()
            with torch.inference_mode():
                return [forward_probabilities(torch, model, tokenizer, row["utterances"], options["device"], length, limit).cpu().tolist() for row in rows]

        output.mkdir(parents=True)
        history, best_score, best_epoch = [], -1, None
        validation_truth = [row["label"] for row in splits["validation"]]
        for epoch in range(options["epochs"]):
            model.train()
            rows = list(splits["train"])
            random.Random(options["seed"] + epoch).shuffle(rows)
            total_loss = 0
            for row in rows:
                optimizer.zero_grad(set_to_none=True)
                probabilities = forward_probabilities(torch, model, tokenizer, row["utterances"], options["device"], length, limit)
                loss = -probabilities[CODES.index(row["label"])].clamp_min(1e-8).log()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                total_loss += loss.item()
            probabilities = predict(splits["validation"])
            metric = scores(validation_truth, [probability_label(p, 0) for p in probabilities])
            history.append({"epoch": epoch + 1, "train_loss": total_loss / len(rows), "validation_macro_f1": metric["macro_f1"]})
            self.stdout.write(json.dumps(history[-1]))
            if metric["macro_f1"] > best_score:
                best_score, best_epoch = metric["macro_f1"], epoch + 1
                model.save_pretrained(str(output), safe_serialization=True)
                tokenizer.save_pretrained(str(output))
        # Reload best epoch chosen exclusively on validation, then choose threshold on validation only.
        del optimizer, model
        if options["device"] == "cuda":
            torch.cuda.empty_cache()
        model = AutoModelForSequenceClassification.from_pretrained(str(output), local_files_only=True, trust_remote_code=False, use_safetensors=True).to(options["device"])
        validation_probs = predict(splits["validation"])
        threshold = select_threshold(validation_truth, validation_probs)
        majority = max(CODES, key=lambda code: sum(row["label"] == code for row in splits["train"]))
        evaluation = {"format": FORMAT, "bundle_sha256": bundle["bundle_sha256"], "definition_hash": bundle["definition_hash"],
            "preprocessing": WINDOWING, "history": history, "best_epoch": best_epoch, "threshold": threshold,
            "threshold_selected_on": "validation", "confidence_calibrated": False, "reports": {}, "baseline": {}}
        for name in ("validation", "test"):
            truth = [row["label"] for row in splits[name]]
            probabilities = validation_probs if name == "validation" else predict(splits[name])
            evaluation["reports"][name] = scores(truth, [probability_label(p, threshold) for p in probabilities])
            evaluation["baseline"][name] = scores(truth, [majority] * len(truth))
        write_json(output / "evaluation.json", evaluation)
        files = {path.name: file_hash(path) for path in output.iterdir() if path.is_file()}
        manifest = {"format": FORMAT, "preprocessing": WINDOWING, "labels": CODES, "definition_hash": bundle["definition_hash"],
            "model_version": "status-" + bundle["bundle_sha256"][:12] + f"-seed{options['seed']}", "bundle_sha256": bundle["bundle_sha256"],
            "threshold": threshold, "max_length": length, "max_windows": limit, "files": files,
            "base_model_config_sha256": file_hash(base / "config.json"), "license_reviewed_for_experiment": True,
            "approved_for_use": False, "seed": options["seed"]}
        write_json(output / "status-manifest.json", manifest)
        self.stdout.write("Đã train và đánh giá; manifest CHƯA duyệt phát hành. Xem evaluation.json, không tự bật AI.")
