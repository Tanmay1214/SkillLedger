import { describe, test, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import { UserProfileCard } from "../components/auth/user-profile-card";
import { useAuth } from "../context/auth-context";

vi.mock("../context/auth-context", () => ({
  useAuth: vi.fn(),
}));

// Mock lucide icons
vi.mock("lucide-react", () => ({
  ExternalLink: () => <span data-testid="external-link" />,
  LogOut: () => <span data-testid="logout-icon" />,
}));

describe("UserProfileCard", () => {
  const mockUser = {
    id: 1,
    github_id: 12345,
    username: "testuser",
    name: "Test User Name",
    email: "test@example.com",
    avatar_url: "http://avatar-url",
    profile_url: "http://github.com/testuser",
    created_at: "2026-06-20",
    updated_at: "2026-06-20",
  };

  test("renders nothing when user is null", () => {
    vi.mocked(useAuth).mockReturnValue({
      status: "unauthenticated",
      user: null,
      loginInProgress: false,
      loginError: null,
      loginWithGithub: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    const { container } = render(<UserProfileCard />);
    expect(container.firstChild).toBeNull();
  });

  test("renders user profile info correctly", () => {
    vi.mocked(useAuth).mockReturnValue({
      status: "authenticated",
      user: mockUser,
      loginInProgress: false,
      loginError: null,
      loginWithGithub: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(<UserProfileCard />);

    // Check user info
    expect(screen.getByText("Test User Name")).toBeInTheDocument();
    expect(screen.getByText("@testuser")).toBeInTheDocument();
    expect(screen.getByText("test@example.com")).toBeInTheDocument();

    const avatar = screen.getByRole("img");
    expect(avatar).toHaveAttribute("src", "http://avatar-url");
    expect(avatar).toHaveAttribute("alt", "testuser's avatar");

    const profileLink = screen.getByText("View GitHub profile").closest("a");
    expect(profileLink).toHaveAttribute("href", "http://github.com/testuser");
  });

  test("calls logout and trigger onLogout prop", async () => {
    const logoutMock = vi.fn().mockResolvedValue(undefined);
    const onLogoutMock = vi.fn();

    vi.mocked(useAuth).mockReturnValue({
      status: "authenticated",
      user: mockUser,
      loginInProgress: false,
      loginError: null,
      loginWithGithub: vi.fn(),
      logout: logoutMock,
      refreshUser: vi.fn(),
    });

    render(<UserProfileCard onLogout={onLogoutMock} />);

    const logoutBtn = screen.getByRole("button", { name: /log out/i });
    fireEvent.click(logoutBtn);

    expect(logoutMock).toHaveBeenCalled();
    await waitFor(() => {
      expect(onLogoutMock).toHaveBeenCalled();
    });
  });
});
