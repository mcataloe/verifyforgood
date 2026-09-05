import { apiEndpoints, type ApiClient } from "@charity-status/shared-api";

export type PortalChatScopedId = number | string;

export interface PortalChatConversation {
  conversation_id: number;
  user_id: PortalChatScopedId;
  organization_id: PortalChatScopedId;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface PortalChatMessage {
  message_id: number;
  conversation_id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface PortalChatOrchestrationSummary {
  route_tier: "low" | "medium" | "high";
  route_reason: string;
  retrieval_mode: "structured" | "semantic" | "hybrid" | "model_only";
  retrieval_reason: string;
  provider: string;
  model: string;
  tool_names: string[];
  invocation_count: number;
}

export interface PortalChatClient {
  createConversation(title?: string): Promise<PortalChatConversation>;
  listConversations(): Promise<PortalChatConversation[]>;
  getConversation(conversationId: number): Promise<{
    conversation: PortalChatConversation;
    messages: PortalChatMessage[];
  }>;
  sendMessage(
    conversationId: number,
    content: string,
  ): Promise<{
    user_message: PortalChatMessage;
    assistant_message: PortalChatMessage;
    orchestration: PortalChatOrchestrationSummary;
  }>;
}

export function portalChatConversationMatchesOrganization(
  conversation: Pick<PortalChatConversation, "organization_id">,
  organizationId: PortalChatScopedId | null | undefined,
) {
  const expected = String(organizationId ?? "").trim();
  return (
    expected.length > 0 && String(conversation.organization_id) === expected
  );
}

export function filterPortalChatConversationsForOrganization(
  conversations: readonly PortalChatConversation[],
  organizationId: PortalChatScopedId | null | undefined,
) {
  return conversations.filter((conversation) =>
    portalChatConversationMatchesOrganization(conversation, organizationId),
  );
}

export function createPortalChatClient(apiClient: ApiClient): PortalChatClient {
  return {
    async createConversation(title) {
      const response = await apiClient.post<
        { conversation: PortalChatConversation },
        { title?: string }
      >(apiEndpoints.chat.createConversation, {
        body: title?.trim() ? { title: title.trim() } : {},
      });
      return response.conversation;
    },
    async listConversations() {
      const response = await apiClient.get<{
        conversations: PortalChatConversation[];
      }>(apiEndpoints.chat.conversations);
      return response.conversations;
    },
    getConversation(conversationId) {
      return apiClient.get<{
        conversation: PortalChatConversation;
        messages: PortalChatMessage[];
      }>(apiEndpoints.chat.conversation, {
        pathParams: { conversationId },
      });
    },
    sendMessage(conversationId, content) {
      return apiClient.post<
        {
          user_message: PortalChatMessage;
          assistant_message: PortalChatMessage;
          orchestration: PortalChatOrchestrationSummary;
        },
        { content: string }
      >(apiEndpoints.chat.sendMessage, {
        pathParams: { conversationId },
        body: { content },
      });
    },
  };
}
