import { describe, it, expect, beforeEach, vi } from "vitest";

import { toast, useToastStore } from "../toast";

describe("toast store", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useToastStore.getState().clear();
  });

  it("pushes error toast and exposes it via store", () => {
    toast.error("Boom");
    const list = useToastStore.getState().toasts;
    expect(list).toHaveLength(1);
    expect(list[0].type).toBe("error");
    expect(list[0].message).toBe("Boom");
  });

  it("auto-dismisses after default 4s", () => {
    toast.info("hi");
    expect(useToastStore.getState().toasts).toHaveLength(1);
    vi.advanceTimersByTime(4000);
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("respects custom durationMs", () => {
    toast.success("ok", { durationMs: 8000 });
    vi.advanceTimersByTime(4000);
    expect(useToastStore.getState().toasts).toHaveLength(1);
    vi.advanceTimersByTime(4000);
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("dismiss(id) removes a single toast", () => {
    const a = toast.info("a");
    toast.info("b");
    toast.dismiss(a);
    const list = useToastStore.getState().toasts;
    expect(list.map((t) => t.message)).toEqual(["b"]);
  });
});
