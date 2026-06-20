import { describe, test, expect, vi, beforeEach } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";
import React from "react";
import { AuthProvider, useAuth } from "../context/auth-context";
import { apiClient } from "../lib/api-client";

// Mock the api-client module
vi.mock("../lib/api-client", () => {
  return {
    apiClient: {
      getMe: vi.fn(),
      getLoginUrl: vi.fn(),
      logout: vi.fn(),
      refresh: vi.fn(),
    },
    ApiError: class ApiError extends Error {
      status: number;
      constructor(message: string, status: number) {
        super(message);
        this.status = status;
      }
    },
  };
});

// A test component to consume the auth context and render its values
function TestConsumer() {
  const { user, status, loginInProgress, loginError, loginWithGithub, logout, refreshUser } = useAuth();
  return (
    <div>
      <div data-testid="status">{status}</div>
      <div data-testid="user">{user ? user.username : "none"}</div>
      <div data-testid="loginInProgress">{loginInProgress ? "true" : "false"}</div>
      <div data-testid="loginError">{loginError ?? "none"}</div>
      <button onClick={loginWithGithub} data-testid="login-btn">Login</button>
      <button onClick={logout} data-testid="logout-btn">Logout</button>
      <button onClick={refreshUser} data-testid="refresh-btn">Refresh</button>
    </div>
  );
}

describe("AuthProvider & useAuth", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("initial loading state and transitions to authenticated on success", async () => {
    const mockUser = {
      id: 1,
      github_id: 12345,
      username: "testuser",
      name: "Test User",
      email: "test@example.com",
      avatar_url: "http://avatar",
      profile_url: "http://profile",
      created_at: "2026-06-20",
      updated_at: "2026-06-20",
    };

    vi.mocked(apiClient.getMe).mockResolvedValue(mockUser);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    // Initial status should be loading
    expect(screen.getByTestId("status")).toHaveTextContent("loading");

    // Wait for the status to change to authenticated
    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
    });

    expect(screen.getByTestId("user")).toHaveTextContent("testuser");
  });

  test("transitions to unauthenticated on 401 error", async () => {
    const { ApiError } = await import("../lib/api-client");
    vi.mocked(apiClient.getMe).mockRejectedValue(new ApiError("Unauthorized", 401));

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
    });
    expect(screen.getByTestId("user")).toHaveTextContent("none");
  });

  test("loginWithGithub triggers redirect on success", async () => {
    const { ApiError } = await import("../lib/api-client");
    vi.mocked(apiClient.getMe).mockRejectedValue(new ApiError("Unauthorized", 401));
    vi.mocked(apiClient.getLoginUrl).mockResolvedValue({
      authorization_url: "https://github.com/login",
      state: "signed-state",
    });

    // Mock window.location.assign
    const assignMock = vi.fn();
    Object.defineProperty(window, "location", {
      writable: true,
      value: { assign: assignMock },
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
    });

    const loginBtn = screen.getByTestId("login-btn");
    act(() => {
      loginBtn.click();
    });

    await waitFor(() => {
      expect(assignMock).toHaveBeenCalledWith("https://github.com/login");
    });
  });

  test("logout calls api and updates status", async () => {
    const mockUser = {
      id: 1,
      github_id: 12345,
      username: "testuser",
      name: "Test User",
      email: "test@example.com",
      avatar_url: "http://avatar",
      profile_url: "http://profile",
      created_at: "2026-06-20",
      updated_at: "2026-06-20",
    };

    vi.mocked(apiClient.getMe).mockResolvedValue(mockUser);
    vi.mocked(apiClient.logout).mockResolvedValue({ message: "Logged out" });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
    });

    const logoutBtn = screen.getByTestId("logout-btn");
    await act(async () => {
      logoutBtn.click();
    });

    expect(apiClient.logout).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
    });
  });
});
