import {
  Alert,
  Badge,
  Button,
  Divider,
  Drawer,
  Group,
  Loader,
  Paper,
  ScrollArea,
  Stack,
  Text,
  Textarea,
} from "@mantine/core";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import { useEffect, useMemo, useRef, useState } from "react";
import { createPortalApiClient } from "../app/portalApiClient";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { usePortalAuth } from "../auth/usePortalAuth";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  createPortalChatClient,
  filterPortalChatConversationsForOrganization,
  portalChatConversationMatchesOrganization,
  type PortalChatConversation,
  type PortalChatMessage,
  type PortalChatOrchestrationSummary,
} from "./chatClient";

interface PortalChatDrawerProps {
  runtimeConfig: FrontendRuntimeConfig;
  session: PortalAuthenticatedSession;
}

export function PortalChatDrawer({
  runtimeConfig,
  session,
}: PortalChatDrawerProps) {
  const auth = usePortalAuth();
  const organization = usePortalOrganization();
  const activeOrganizationId = String(
    organization.activeOrganization.organization_id ?? "",
  ).trim();
  const activeOrganizationIdRef = useRef(activeOrganizationId);
  activeOrganizationIdRef.current = activeOrganizationId;

  const apiClient = useMemo(
    () =>
      createPortalApiClient({
        accessToken: auth.accessToken,
        context: organization,
        runtimeConfig,
        session,
      }),
    [auth.accessToken, organization, runtimeConfig, session],
  );
  const chatClient = useMemo(() => createPortalChatClient(apiClient), [apiClient]);
  const chatAvailable =
    session.organization_context_status === "active" &&
    Boolean(auth.accessToken) &&
    Boolean(activeOrganizationId);

  const [opened, setOpened] = useState(false);
  const [conversations, setConversations] = useState<PortalChatConversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<PortalChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scopeMismatch, setScopeMismatch] = useState(false);
  const [lastOrchestration, setLastOrchestration] =
    useState<PortalChatOrchestrationSummary | null>(null);

  useEffect(() => {
    setConversations([]);
    setActiveConversationId(null);
    setMessages([]);
    setDraft("");
    setBusy(false);
    setError(null);
    setScopeMismatch(false);
    setLastOrchestration(null);
  }, [activeOrganizationId]);

  const requestStillMatchesScope = (requestScope: string) =>
    requestScope === activeOrganizationIdRef.current;

  const loadConversations = async () => {
    if (!chatAvailable) {
      return;
    }
    const requestScope = activeOrganizationIdRef.current;
    setBusy(true);
    setError(null);
    try {
      const loaded = await chatClient.listConversations();
      if (!requestStillMatchesScope(requestScope)) {
        return;
      }
      const matching = filterPortalChatConversationsForOrganization(
        loaded,
        requestScope,
      );
      const mismatch = loaded.length !== matching.length;
      setScopeMismatch(mismatch);
      setConversations(matching);
      if (mismatch) {
        setActiveConversationId(null);
        setMessages([]);
      }
    } catch (nextError) {
      if (requestStillMatchesScope(requestScope)) {
        setError(resolveErrorMessage(nextError));
      }
    } finally {
      if (requestStillMatchesScope(requestScope)) {
        setBusy(false);
      }
    }
  };

  const createConversation = async () => {
    if (!chatAvailable) {
      return null;
    }
    const requestScope = activeOrganizationIdRef.current;
    setBusy(true);
    setError(null);
    try {
      const conversation = await chatClient.createConversation();
      if (!requestStillMatchesScope(requestScope)) {
        return null;
      }
      if (!portalChatConversationMatchesOrganization(conversation, requestScope)) {
        setScopeMismatch(true);
        setConversations([]);
        setActiveConversationId(null);
        setMessages([]);
        return null;
      }
      setScopeMismatch(false);
      setConversations((current) => [
        conversation,
        ...current.filter(
          (item) => item.conversation_id !== conversation.conversation_id,
        ),
      ]);
      setActiveConversationId(conversation.conversation_id);
      setMessages([]);
      setLastOrchestration(null);
      return conversation;
    } catch (nextError) {
      if (requestStillMatchesScope(requestScope)) {
        setError(resolveErrorMessage(nextError));
      }
      return null;
    } finally {
      if (requestStillMatchesScope(requestScope)) {
        setBusy(false);
      }
    }
  };

  const openConversation = async (conversation: PortalChatConversation) => {
    const requestScope = activeOrganizationIdRef.current;
    if (!portalChatConversationMatchesOrganization(conversation, requestScope)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const loaded = await chatClient.getConversation(conversation.conversation_id);
      if (!requestStillMatchesScope(requestScope)) {
        return;
      }
      if (!portalChatConversationMatchesOrganization(loaded.conversation, requestScope)) {
        setScopeMismatch(true);
        setActiveConversationId(null);
        setMessages([]);
        return;
      }
      setScopeMismatch(false);
      setActiveConversationId(conversation.conversation_id);
      setMessages(loaded.messages);
      setLastOrchestration(null);
    } catch (nextError) {
      if (requestStillMatchesScope(requestScope)) {
        setError(resolveErrorMessage(nextError));
      }
    } finally {
      if (requestStillMatchesScope(requestScope)) {
        setBusy(false);
      }
    }
  };

  const sendMessage = async () => {
    const content = draft.trim();
    if (!content || busy || scopeMismatch || !chatAvailable) {
      return;
    }
    const requestScope = activeOrganizationIdRef.current;
    setBusy(true);
    setError(null);
    try {
      let conversationId = activeConversationId;
      if (!conversationId) {
        const conversation = await chatClient.createConversation();
        if (!requestStillMatchesScope(requestScope)) {
          return;
        }
        if (!portalChatConversationMatchesOrganization(conversation, requestScope)) {
          setScopeMismatch(true);
          return;
        }
        conversationId = conversation.conversation_id;
        setConversations((current) => [conversation, ...current]);
        setActiveConversationId(conversationId);
      }
      const response = await chatClient.sendMessage(conversationId, content);
      if (!requestStillMatchesScope(requestScope)) {
        return;
      }
      setMessages((current) => [
        ...current,
        response.user_message,
        response.assistant_message,
      ]);
      setLastOrchestration(response.orchestration);
      setDraft("");
    } catch (nextError) {
      if (requestStillMatchesScope(requestScope)) {
        setError(resolveErrorMessage(nextError));
      }
    } finally {
      if (requestStillMatchesScope(requestScope)) {
        setBusy(false);
      }
    }
  };

  return (
    <>
      <Button
        aria-label="Open Chat"
        disabled={!chatAvailable}
        size="compact-sm"
        variant="light"
        onClick={() => {
          setOpened(true);
          void loadConversations();
        }}
      >
        Chat
      </Button>
      <Drawer
        opened={opened}
        onClose={() => setOpened(false)}
        position="right"
        size="lg"
        title="VerifyForGood Chat"
      >
        <Stack gap="md" h="calc(100vh - 100px)">
          <Text c="dimmed" size="sm">
            Local Chat validates retrieval and orchestration plumbing. Local model
            answer quality is not a production-quality signal.
          </Text>

          {!chatAvailable ? (
            <Alert title="Organization required">
              Chat is available after an authenticated organization context is active.
            </Alert>
          ) : null}
          {scopeMismatch ? (
            <Alert color="yellow" title="Organization context changed">
              Chat history is hidden because the server-resolved organization does
              not match the organization selected in the portal. Refresh the
              authenticated organization context before using Chat for this workspace.
            </Alert>
          ) : null}
          {error ? <Alert color="red">{error}</Alert> : null}

          <Group justify="space-between" align="center">
            <Text fw={600} size="sm">
              Conversations
            </Text>
            <Button
              size="compact-xs"
              variant="default"
              disabled={busy || scopeMismatch || !chatAvailable}
              onClick={() => void createConversation()}
            >
              New
            </Button>
          </Group>

          <ScrollArea h={110} type="auto">
            <Group gap="xs" wrap="wrap">
              {conversations.map((conversation) => (
                <Button
                  key={conversation.conversation_id}
                  size="compact-xs"
                  variant={
                    activeConversationId === conversation.conversation_id
                      ? "filled"
                      : "light"
                  }
                  onClick={() => void openConversation(conversation)}
                >
                  {conversation.title}
                </Button>
              ))}
              {!conversations.length && !busy ? (
                <Text c="dimmed" size="sm">
                  No conversations for this organization.
                </Text>
              ) : null}
            </Group>
          </ScrollArea>

          <Divider />

          <ScrollArea flex={1} type="auto">
            <Stack gap="sm" pr="xs">
              {messages.map((message) => (
                <Paper key={message.message_id} p="sm" withBorder>
                  <Text fw={600} size="xs" tt="uppercase" c="dimmed">
                    {message.role === "user" ? "You" : "Assistant"}
                  </Text>
                  <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                    {message.content}
                  </Text>
                </Paper>
              ))}
              {busy ? (
                <Group gap="xs">
                  <Loader size="sm" />
                  <Text c="dimmed" size="sm">
                    Running local Chat pipeline…
                  </Text>
                </Group>
              ) : null}
            </Stack>
          </ScrollArea>

          {lastOrchestration ? (
            <Group gap="xs">
              <Badge variant="light">{lastOrchestration.route_tier}</Badge>
              <Badge variant="light">{lastOrchestration.retrieval_mode}</Badge>
              <Text c="dimmed" size="xs">
                {lastOrchestration.provider} / {lastOrchestration.model}
              </Text>
            </Group>
          ) : null}

          <Textarea
            autosize
            minRows={2}
            maxRows={6}
            disabled={busy || scopeMismatch || !chatAvailable}
            label="Message"
            placeholder="Ask about nonprofit data or your organization account…"
            value={draft}
            onChange={(event) => setDraft(event.currentTarget.value)}
          />
          <Button
            disabled={!draft.trim() || busy || scopeMismatch || !chatAvailable}
            onClick={() => void sendMessage()}
          >
            Send
          </Button>
        </Stack>
      </Drawer>
    </>
  );
}

function resolveErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Chat request failed.";
}
