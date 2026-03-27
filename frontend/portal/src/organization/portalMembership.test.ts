import { describe, expect, it, vi } from "vitest";
import type { ApiClient } from "@charity-status/shared-api";
import {
  createPortalMembershipClient,
} from "./portalMembership";

describe("portalMembership client", () => {
  it("lists members from the current organization endpoint", async () => {
    const get = vi.fn(async () => ({
      items: [
        {
          created_at: "2026-03-27T00:00:00Z",
          email: "jamie.admin@example.org",
          full_name: "Jamie Admin",
          role: "admin",
          status: "active",
          updated_at: "2026-03-27T00:00:00Z",
          user_id: "user_jamie_admin",
        },
      ],
    }));
    const client = createPortalMembershipClient({
      delete: vi.fn(),
      get,
      patch: vi.fn(),
      post: vi.fn(),
      requestData: vi.fn(),
      requestEnvelope: vi.fn(),
      put: vi.fn(),
    } as unknown as ApiClient);

    const items = await client.listMembers();

    expect(get).toHaveBeenCalledOnce();
    expect(items[0]?.role).toBe("admin");
  });

  it("uses member-scoped paths for role updates and removals", async () => {
    const patch = vi.fn(async () => ({
      created_at: "2026-03-27T00:00:00Z",
      email: "member@example.org",
      full_name: "Member User",
      role: "admin",
      status: "active",
      updated_at: "2026-03-28T00:00:00Z",
      user_id: "user_member",
    }));
    const deleteMember = vi.fn(async () => ({
      organization_id: "org_123",
      removed_member_id: "user_member",
    }));
    const client = createPortalMembershipClient({
      delete: deleteMember,
      get: vi.fn(),
      patch,
      post: vi.fn(),
      requestData: vi.fn(),
      requestEnvelope: vi.fn(),
      put: vi.fn(),
    } as unknown as ApiClient);

    await client.updateMember("user_member", { role: "admin" });
    await client.removeMember("user_member");

    const patchTarget = (patch.mock.calls as unknown[][])[0]?.[0];
    const deleteTarget = (deleteMember.mock.calls as unknown[][])[0]?.[0];

    expect(String(patchTarget)).toContain(
      "/organizations/current/members/user_member",
    );
    expect(String(deleteTarget)).toContain(
      "/organizations/current/members/user_member",
    );
  });
});
