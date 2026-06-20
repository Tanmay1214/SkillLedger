import { describe, test, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { ProtectedRoute } from "../components/auth/protected-route";
import { useAuth } from "../context/auth-context";
import { useRouter } from "next/navigation";

// Mock useAuth
vi.mock("../context/auth-context", () => ({
  useAuth: vi.fn(),
}));

// Mock useRouter
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

// Mock Spinner
vi.mock("../components/ui/spinner", () => ({
  Spinner: () => <div data-testid="spinner-mock">Spinner</div>,
}));

describe("ProtectedRoute", () => {
  test("renders children when status is authenticated", () => {
    vi.mocked(useAuth).mockReturnValue({
      status: "authenticated",
      user: null,
      loginInProgress: false,
      loginError: null,
      loginWithGithub: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(
      <ProtectedRoute>
        <div data-testid="child">Protected Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByTestId("child")).toHaveTextContent("Protected Content");
    expect(screen.queryByTestId("spinner-mock")).not.toBeInTheDocument();
  });

  test("renders spinner when status is loading", () => {
    vi.mocked(useAuth).mockReturnValue({
      status: "loading",
      user: null,
      loginInProgress: false,
      loginError: null,
      loginWithGithub: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(
      <ProtectedRoute>
        <div data-testid="child">Protected Content</div>
      </ProtectedRoute>
    );

    expect(screen.queryByTestId("child")).not.toBeInTheDocument();
    expect(screen.getByTestId("spinner-mock")).toBeInTheDocument();
  });

  test("redirects and returns null when status is unauthenticated", () => {
    const replaceMock = vi.fn();
    vi.mocked(useRouter).mockReturnValue({
      replace: replaceMock,
    } as unknown as ReturnType<typeof useRouter>);

    vi.mocked(useAuth).mockReturnValue({
      status: "unauthenticated",
      user: null,
      loginInProgress: false,
      loginError: null,
      loginWithGithub: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    const { container } = render(
      <ProtectedRoute redirectTo="/login">
        <div data-testid="child">Protected Content</div>
      </ProtectedRoute>
    );

    expect(container.firstChild).toBeNull();
    expect(replaceMock).toHaveBeenCalledWith("/login");
  });
});
