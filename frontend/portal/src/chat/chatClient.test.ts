import { apiEndpoints, type ApiClient } from "@charity-status/shared-api";
import { describe, expect, it, vi } from "vitest";
import {
  createPortalChatClient,
  filterPortalChatConversationsForOrganization,
  portalChatConversationMatchesOrganization,
  type PortalChatConversation,
} from "./chatClient";

function conversation(
  overrides: Partial<PortalChatConversation> = {},
): PortalChatConversation {
  return {
    conversation_id: 1,
    user_id: 10,
    organization_id: 20,
    title: "Conversation",
    created_at: "2026-09-05T10:00:00Z",
    updated_at: "2026-09-05T10:00:00Z",
    ...overrides,
  };
}

function makeApiClient() {
  const get = vi.fn();
  const post = vi.fn();
  const client = {
    delete: vi.fn(),
    get,
    patch: vi.fn(),
    post,
    put: vi.fn(),
    requestData: vi.fn(),
    requestEnvelope: vi.fn(),
  } as unknown as ApiClient;
  return { client, get, post };
}

describe("portal Chat client", () => {
  it("uses the shared Chat endpoints and trims a conversation title", async () => {
    const { client: apiClient, post } = makeApiClient();
    const expected = conversation();
    post.mockResolvedValueOnce({ conversation: expected });

    const client = createPortalChatClient(apiClient);
    await expect(client.createConversation("  Review Acme  ")).resolves.toEqual(
      expected,
    );

    expect(post).toHaveBeenCalledWith(apiEndpoints.chat.createConversation, {
      body: { title: "Review Acme" },
    });
  });

  it("passes conversation ids only as path parameters", async () => {
    const { client: apiClient, get, post } = makeApiClient();
    get.mockResolvedValueOnce({
      conversation: conversation({ conversation_id: 7 }),
      messages: [],
    });
    post.mockResolvedValueOnce({
      user_message: {},
      assistant_message: {},
      orchestration: {},
    });

    const client = createPortalChatClient(apiClient);
    await client.getConversation(7);
    await client.sendMessage(7, "hello");

    expect(get).toHaveBeenCalledWith(apiEndpoints.chat.conversation, {
      pathParams: { conversationId: 7 },
    });
    expect(post).toHaveBeenCalledWith(apiEndpoints.chat.sendMessage, {
      pathParams: { conversationId: 7 },
      body: { content: "hello" },
    });
  });

  it("matches organization scope across numeric and string ids", () => {
    const first = conversation({ conversation_id: 1, organization_id: 42 });
    const second = conversation({ conversation_id: 2, organization_id: "99" });

    expect(portalChatConversationMatchesOrganization(first, "42")).toBe(true);
    expect(portalChatConversationMatchesOrganization(second, 99)).toBe(true);
    expect(portalChatConversationMatchesOrganization(second, 42)).toBe(false);
    expect(
      filterPortalChatConversationsForOrganization([first, second], "42"),
    ).toEqual([first]);
  });
});
