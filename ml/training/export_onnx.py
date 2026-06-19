"""Export a trained MobileNetV3-Small checkpoint and create an INT8 ONNX model."""

import argparse
from pathlib import Path

import torch
from onnxruntime.quantization import QuantType, quantize_dynamic

from train_mobilenetv3 import build_model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", type=Path, default=Path("ml/models/disease_mobilenetv3_int8.onnx"))
    args = parser.parse_args()
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    model = build_model(len(checkpoint["labels"]))
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    fp32 = args.output.with_name("disease_mobilenetv3_fp32.onnx")
    torch.onnx.export(
        model,
        torch.zeros(1, 3, 224, 224),
        fp32,
        input_names=["image"],
        output_names=["logits"],
        dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
    )
    quantize_dynamic(fp32, args.output, weight_type=QuantType.QInt8)
    print(f"Exported {args.output}")


if __name__ == "__main__":
    main()

