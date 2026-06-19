import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FeatureCard } from "./FeatureCard";
import type { FeatureResult } from "../types";

const disease: FeatureResult = {
  feature: "disease",
  title: "Disease detection",
  title_ar: "كشف الأمراض",
  level: "experimental",
  score: 0.9,
  value: "Cordana leaf spot",
  value_ar: "تبقع أوراق الكوردانا",
  confidence: 0.9,
  evidence: ["Real ONNX model inference"],
  limitation: "Model audit limitations apply.",
  disease_info: {
    key: "cordana_leaf_spot",
    name_en: "Cordana leaf spot",
    name_ar: "تبقع أوراق الكوردانا",
    summary_en: "Reviewed summary.",
    summary_ar: "ملخص مراجع.",
    symptoms_en: ["Brown lesions"],
    symptoms_ar: ["بقع بنية"],
    management_en: ["Get field confirmation"],
    management_ar: ["اطلب تأكيدًا ميدانيًا"]
  }
};

describe("FeatureCard", () => {
  it("shows real AI labeling, asserts no Open diagnosis details button on disease card, and applies card tilt", () => {
    const { container } = render(<FeatureCard result={disease} arabic={false} />);
    const card = container.querySelector(".feature-card") as HTMLElement;
    vi.spyOn(card, "getBoundingClientRect").mockReturnValue({
      x: 0, y: 0, top: 0, left: 0, right: 200, bottom: 100, width: 200, height: 100, toJSON: () => ({})
    });

    expect(screen.getByText("Strong visual match")).toBeInTheDocument();
    // Assert "Open diagnosis details" button is NOT rendered on disease cards
    expect(screen.queryByRole("button", { name: /Open diagnosis details/ })).not.toBeInTheDocument();

    // Gentle tilt: a small rotation is applied (no jarring translateZ pop), and it
    // resets cleanly on mouse leave so the card content stays readable and clickable.
    fireEvent.mouseMove(card, { clientX: 150, clientY: 25 });
    expect(card.style.getPropertyValue("--tz")).toBe("0px");
    expect(card.style.getPropertyValue("--ry")).not.toBe("0deg");
    fireEvent.mouseLeave(card);
    expect(card.style.getPropertyValue("--ry")).toBe("0deg");
  });

  it("expands disease details on non-disease feature cards and supports Arabic modal", () => {
    const nonDisease = { ...disease, feature: "vegetation" };
    render(<FeatureCard result={nonDisease} arabic={false} />);
    
    const toggleButton = screen.getByRole("button", { name: /Open diagnosis details/ });
    expect(toggleButton).toBeInTheDocument();
    fireEvent.click(toggleButton);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Reviewed summary.")).toBeInTheDocument();
    expect(screen.getByText("Brown lesions")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByText("Reviewed summary.")).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe("");
  });

  it("renders Arabic disease details for non-disease card", () => {
    const nonDisease = { ...disease, feature: "vegetation" };
    render(<FeatureCard result={nonDisease} arabic />);
    expect(screen.getByText("نسبة التأكد")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /افتح تفاصيل التشخيص/ }));
    expect(screen.getByText("ملخص مراجع.")).toBeInTheDocument();
  });

  it("labels a rejected image match without claiming a diagnosis", () => {
    render(
      <FeatureCard
        result={{
          ...disease,
          level: "sample-data",
          value: "No reliable tomato diagnosis from this photo",
          disease_info: undefined,
        }}
        arabic={false}
      />
    );

    expect(screen.getByText("No reliable match")).toBeInTheDocument();
    expect(screen.getByText("Visual match score (not diagnosis)")).toBeInTheDocument();
    expect(screen.queryByText("Strong visual match")).not.toBeInTheDocument();
  });
});
