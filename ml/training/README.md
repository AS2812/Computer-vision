# Lightweight training pipeline

The local demo intentionally does not bundle unverified third-party disease weights.
Fine-tune `MobileNetV3-Small` on licensed crop-specific data, evaluate on field photos,
then export and quantize to ONNX.

Expected gates before updating `ml/models/manifest.json`:

- macro-F1 >= 0.90 on the held-out supported-crop set
- per-class recall >= 0.80
- INT8 macro-F1 loss <= 0.02 versus FP32
- CPU inference p95 <= 1 second for a 224x224 image
- peak API memory below 4 GB

