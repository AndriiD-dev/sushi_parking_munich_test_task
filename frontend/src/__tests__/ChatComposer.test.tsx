/**
 * Tests for the ChatComposer component.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ChatComposer from "../components/ChatComposer";

describe("ChatComposer", () => {
  it("renders input and send button", () => {
    render(<ChatComposer onSubmit={vi.fn()} isLoading={false} />);

    expect(screen.getByLabelText("Chat message input")).toBeInTheDocument();
    expect(screen.getByLabelText("Send message")).toBeInTheDocument();
  });

  it("calls onSubmit with trimmed text on form submit", () => {
    const onSubmit = vi.fn();
    render(<ChatComposer onSubmit={onSubmit} isLoading={false} />);

    const input = screen.getByLabelText("Chat message input");
    fireEvent.change(input, { target: { value: "  Hello world  " } });
    fireEvent.submit(input.closest("form")!);

    expect(onSubmit).toHaveBeenCalledWith("Hello world");
  });

  it("clears input after submission", () => {
    render(<ChatComposer onSubmit={vi.fn()} isLoading={false} />);

    const input = screen.getByLabelText(
      "Chat message input",
    ) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Test" } });
    fireEvent.submit(input.closest("form")!);

    expect(input.value).toBe("");
  });

  it("disables input and button when loading", () => {
    render(<ChatComposer onSubmit={vi.fn()} isLoading={true} />);

    expect(screen.getByLabelText("Chat message input")).toBeDisabled();
    expect(screen.getByLabelText("Send message")).toBeDisabled();
  });

  it("disables send button when input is empty", () => {
    render(<ChatComposer onSubmit={vi.fn()} isLoading={false} />);
    expect(screen.getByLabelText("Send message")).toBeDisabled();
  });

  it("does not call onSubmit on empty input", () => {
    const onSubmit = vi.fn();
    render(<ChatComposer onSubmit={onSubmit} isLoading={false} />);

    const input = screen.getByLabelText("Chat message input");
    fireEvent.submit(input.closest("form")!);

    expect(onSubmit).not.toHaveBeenCalled();
  });
});
