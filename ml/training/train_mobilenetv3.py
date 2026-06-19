"""Fine-tune MobileNetV3-Small from an ImageFolder dataset."""

import argparse
import json
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms


def build_model(class_count: int) -> nn.Module:
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, class_count)
    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("ml/models/disease_mobilenetv3_fp32.pt"))
    args = parser.parse_args()

    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
    ])
    val_transform = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()])
    train_set = datasets.ImageFolder(args.dataset / "train", transform=train_transform)
    val_set = datasets.ImageFolder(args.dataset / "val", transform=val_transform)
    train_loader = DataLoader(train_set, batch_size=32, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_set, batch_size=32, num_workers=0)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(len(train_set.classes)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(args.epochs):
        model.train()
        for images, labels in train_loader:
            optimizer.zero_grad()
            loss = criterion(model(images.to(device)), labels.to(device))
            loss.backward()
            optimizer.step()
        model.eval()
        correct = total = 0
        with torch.no_grad():
            for images, labels in val_loader:
                predictions = model(images.to(device)).argmax(dim=1).cpu()
                correct += int((predictions == labels).sum())
                total += len(labels)
        print(f"epoch={epoch + 1} validation_accuracy={correct / max(total, 1):.4f}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.cpu().state_dict(), "labels": train_set.classes}, args.output)
    args.output.with_suffix(".labels.json").write_text(json.dumps(train_set.classes), encoding="utf-8")


if __name__ == "__main__":
    main()

