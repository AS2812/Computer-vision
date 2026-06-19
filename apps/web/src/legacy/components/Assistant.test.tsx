import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import { Assistant } from "./Assistant";

afterEach(() => vi.restoreAllMocks());

describe("Assistant", () => {
  it("shows a grounded online response and closes with Escape", async () => {
    vi.spyOn(api, "assistant").mockResolvedValue({
      answer: "**Measured result**",
      sources: ["https://example.com/reviewed"],
      mode: "external-grounded-assistant"
    });
    render(<Assistant analysisId="analysis-1" arabic={false} />);

    fireEvent.click(screen.getByLabelText("Ask AI"));
    expect(document.body.style.overflow).toBe("hidden");
    fireEvent.change(screen.getByPlaceholderText("Ask about your crop…"), { target: { value: "Explain this" } });
    fireEvent.click(screen.getByLabelText("Send question"));

    await waitFor(() => expect(screen.getByText("Measured result")).toBeInTheDocument());
    expect(screen.getByText("Online")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Reviewed source" })).toHaveAttribute("href", "https://example.com/reviewed");
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.getByLabelText("Ask AI")).not.toHaveClass("is-hidden");
    expect(document.body.style.overflow).toBe("");
  });

  it("offers case-specific treatment questions", async () => {
    const request = vi.spyOn(api, "assistant").mockResolvedValue({
      answer: "Treatment guidance.",
      sources: [],
      mode: "offline-grounded-template"
    });
    render(
      <Assistant
        analysisId="analysis-1"
        arabic={false}
        quickQuestions={[{ en: "What is the safest treatment plan for Cordana?", ar: "ما هي خطة العلاج؟" }]}
      />
    );

    fireEvent.click(screen.getByLabelText("Ask AI"));
    fireEvent.click(screen.getByRole("button", { name: "What is the safest treatment plan for Cordana?" }));

    await waitFor(() => expect(request).toHaveBeenCalledWith("What is the safest treatment plan for Cordana?", "analysis-1", "en"));
    expect(screen.getByText("Treatment guidance.")).toBeInTheDocument();
  });

  it("shows error mode and closes from the backdrop", async () => {
    vi.spyOn(api, "assistant").mockRejectedValue(new Error("offline"));
    const { container } = render(<Assistant arabic={false} />);

    fireEvent.click(screen.getByLabelText("Ask AI"));
    fireEvent.change(screen.getByPlaceholderText("Ask about your crop…"), { target: { value: "Help" } });
    fireEvent.click(screen.getByLabelText("Send question"));

    await waitFor(() => expect(screen.getByText("Offline")).toBeInTheDocument());
    fireEvent.click(container.querySelector(".chat-backdrop") as HTMLElement);
    expect(screen.getByLabelText("Ask AI")).not.toHaveClass("is-hidden");
  });
});
