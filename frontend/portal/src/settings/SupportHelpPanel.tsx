import { useState } from "react";
import {
  Button,
  NativeSelect,
  Stack,
  TagsInput,
  TextInput,
  Textarea,
} from "@mantine/core";
import {
  PortalActionGroup,
  PortalDetailList,
  PortalHint,
} from "../components/PortalPrimitives";
import {
  PortalErrorState,
  PortalLoadingState,
  PortalNotice,
} from "../components/feedback";
import type { PortalSupportController } from "./usePortalSupport";

interface SupportHelpPanelProps {
  controller: PortalSupportController;
  pane?: "contact" | "report";
}

const supportCategories = [
  { label: "Account access", value: "account_access" },
  { label: "Billing", value: "billing" },
  { label: "API", value: "api" },
  { label: "Data quality", value: "data_quality" },
  { label: "Nonprofit access", value: "nonprofit_access" },
  { label: "Recommendation", value: "recommendation" },
  { label: "Settings", value: "settings" },
  { label: "Other", value: "other" },
] as const;

export function SupportHelpPanel({
  controller,
  pane,
}: SupportHelpPanelProps) {
  const [category, setCategory] = useState<
    (typeof supportCategories)[number]["value"]
  >("other");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [watchers, setWatchers] = useState<string[]>([]);
  const [watcherMessage, setWatcherMessage] = useState<string | null>(null);

  const validationMessage = getValidationMessage({
    category,
    description,
    subject,
    watcherMessage,
  });

  if (controller.isLoading) {
    return (
      <PortalLoadingState
        subtitle="Loading support details for your organization."
        title="Loading support"
      >
        <p>Preparing contact details and help options.</p>
      </PortalLoadingState>
    );
  }

  if (controller.error && controller.context === null) {
    return (
      <PortalErrorState
        actionLabel="Retry support"
        message={controller.error}
        onAction={() => {
          void controller.reload();
        }}
        subtitle="We couldn't load support details for your organization."
        title="Support unavailable"
      />
    );
  }

  const context = controller.context;
  if (!context) {
    return (
      <PortalNotice title="Support unavailable" tone="empty">
        <p>Support details are not available right now.</p>
      </PortalNotice>
    );
  }

  const submitterEmail = context.account_context.contact_email?.trim() || null;

  return (
    <Stack gap="md">
      {(pane ?? "contact") === "contact" ? (
        <Stack gap="md">
          <PortalHint>{context.issue_reporting.honesty_notice}</PortalHint>
          <PortalDetailList
            items={[
              {
                key: "support-email",
                label: "Support email",
                value: (
                  <a href={context.support_contact.support_mailto}>
                    {context.support_contact.support_email}
                  </a>
                ),
              },
              {
                key: "brand",
                label: "Brand",
                value: context.support_contact.brand_name,
              },
              {
                key: "homepage",
                label: "Homepage",
                value: (
                  <a
                    href={context.support_contact.homepage_url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {context.support_contact.homepage_url}
                  </a>
                ),
              },
              {
                key: "helpful-links",
                label: "Helpful links",
                value: (
                  <>
                    <a href={context.product_links.api_access_hash}>API access</a>
                    {" | "}
                    <a href={context.product_links.usage_hash}>Usage</a>
                    {" | "}
                    <a href={context.product_links.billing_hash}>Billing</a>
                  </>
                ),
              },
            ]}
          />
          <PortalHint>{context.issue_reporting.urgent_contact_notice}</PortalHint>
        </Stack>
      ) : null}

      {(pane ?? "report") === "report" ? (
        <Stack gap="md">
          <NativeSelect
            data={supportCategories.map((option) => ({
              label: option.label,
              value: option.value,
            }))}
            description="Use Recommendation for constructive feedback or feature suggestions."
            id="support-category"
            label="Category"
            onChange={(value) => {
              controller.clearReceipt();
              setCategory(
                (value.currentTarget.value ||
                  "other") as (typeof supportCategories)[number]["value"],
              );
            }}
            value={category}
          />

          <TagsInput
            clearable
            data={[]}
            description={`Replies go to ${submitterEmail ?? "the signed-in account"} by default. Add other email addresses here to keep them copied on follow-up.`}
            label="Watchers"
            onChange={(values) => {
              controller.clearReceipt();
              setWatchers(values);
              const invalidWatcher = values.find((value) => !isValidEmail(value));
              setWatcherMessage(
                invalidWatcher ? "Watchers must be valid email addresses." : null,
              );
            }}
            placeholder="Add email and press Enter"
            value={watchers}
          />

          <TextInput
            id="support-subject"
            label="Subject"
            onChange={(event) => {
              controller.clearReceipt();
              setSubject(event.target.value);
            }}
            placeholder="Short summary of the issue"
            value={subject}
          />

          <Textarea
            autosize
            id="support-description"
            label="Description"
            minRows={5}
            onChange={(event) => {
              controller.clearReceipt();
              setDescription(event.target.value);
            }}
            placeholder="Describe the issue, what you expected, and what happened."
            value={description}
          />

          {validationMessage ? (
            <div className="portal-support-help-panel__notice">
              <PortalNotice tone="error">
                <p>{validationMessage}</p>
              </PortalNotice>
            </div>
          ) : null}

          {controller.error ? (
            <div className="portal-support-help-panel__notice">
              <PortalNotice tone="error">
                <p>{controller.error}</p>
              </PortalNotice>
            </div>
          ) : null}

          {controller.receipt ? (
            <div className="portal-support-help-panel__notice">
              <PortalNotice title="Support request sent" tone="warning">
                <p>
                  Your request was sent on{" "}
                  {formatDateTime(controller.receipt.submitted_at)}. We'll follow up
                  through {controller.receipt.support_email}.
                </p>
              </PortalNotice>
            </div>
          ) : null}

          <PortalActionGroup>
            <Button
              disabled={controller.isSubmitting || validationMessage !== null}
              loading={controller.isSubmitting}
              onClick={() => {
                const cleanedWatchers = watchers
                  .map((value) => value.trim().toLowerCase())
                  .filter(Boolean);
                if (cleanedWatchers.some((value) => !isValidEmail(value))) {
                  setWatcherMessage("Watchers must be valid email addresses.");
                  return;
                }
                void controller
                  .submit({
                    category,
                    context: {
                      current_route_hash:
                        typeof window === "undefined"
                          ? "#/support?nav=customer-admin-support-report-issue"
                          : window.location.hash ||
                            "#/support?nav=customer-admin-support-report-issue",
                      user_agent:
                        typeof navigator === "undefined"
                          ? null
                          : navigator.userAgent,
                    },
                    description: description.trim(),
                    subject: subject.trim(),
                    watchers: cleanedWatchers.length > 0 ? cleanedWatchers : null,
                  })
                  .then(() => {
                    setSubject("");
                    setDescription("");
                    setWatchers([]);
                    setWatcherMessage(null);
                  })
                  .catch(() => {});
              }}
              type="button"
            >
              {controller.isSubmitting
                ? "Sending support request..."
                : "Send support request"}
            </Button>
          </PortalActionGroup>
        </Stack>
      ) : null}
    </Stack>
  );
}

function getValidationMessage(input: {
  category: string;
  description: string;
  subject: string;
  watcherMessage: string | null;
}): string | null {
  if (!input.category) {
    return "Category is required.";
  }
  if (input.subject.trim().length < 3) {
    return "Subject must be at least 3 characters.";
  }
  if (input.description.trim().length < 10) {
    return "Description must be at least 10 characters.";
  }
  if (input.watcherMessage) {
    return input.watcherMessage;
  }
  return null;
}

function formatDateTime(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }
  return new Date(parsed).toLocaleString();
}

function isValidEmail(value: string): boolean {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim());
}
