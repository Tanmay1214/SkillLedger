import { describe, test, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { GithubLoginButton } from "../components/auth/github-login-button";
import { useAuth } from "../context/auth-context";

vi.mock("../context/auth-context", () => ({
  useAuth: vi.fn(),
}));

vi.mock("../components/ui/spinner", () => ({
  Spinner: () => <div data-testid="spinner">Loading...</div>,
}));

describe("GithubLoginButton", () => {
  test("renders standard button state and calls login on click", () => {
    const loginMock = vi.fn();
    vi.mocked(useAuth).mockReturnValue({
      status: "unauthenticated",
      user: null,
      loginInProgress: false,
      loginError: null,
      loginWithGithub: loginMock,
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(<GithubLoginButton />);

    const button = screen.getByRole("button");
    expect(button).toHaveTextContent("Continue with GitHub");
    expect(button).not.toBeDisabled();

    fireEvent.click(button);
    expect(loginMock).toHaveBeenCalled();
  });

  test("renders custom label", () => {
    vi.mocked(useAuth).mockReturnValue({
      status: "unauthenticated",
      user: null,
      loginInProgress: false,
      loginError: null,
      loginWithGithub: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(<GithubLoginButton label="Sign in with GitHub" />);
    expect(screen.getByRole("button")).toHaveTextContent("Sign in with GitHub");
  });

  test("renders loading state when loginInProgress is true", () => {
    vi.mocked(useAuth).mockReturnValue({
      status: "unauthenticated",
      user: null,
      loginInProgress: true,
      loginError: null,
      loginWithGithub: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(<GithubLoginButton />);

    const button = screen.getByRole("button");
    expect(button).toHaveTextContent("Redirecting to GitHub…");
    expect(button).toBeDisabled();
    expect(screen.getByTestId("spinner")).toBeInTheDocument();
  });

  test("renders error message when loginError is present", () => {
    vi.mocked(useAuth).mockReturnValue({
      status: "unauthenticated",
      user: null,
      loginInProgress: false,
      loginError: "OAuth flow failed",
      loginWithGithub: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(<GithubLoginButton />);
    expect(screen.getByRole("alert")).toHaveTextContent("OAuth flow failed");
  });
});
