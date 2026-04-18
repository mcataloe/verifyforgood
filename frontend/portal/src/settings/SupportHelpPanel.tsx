import { useEffect, useState } from "react";
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
  const [replyEmail, setReplyEmail] = useState("");

  useEffect(() => {
    if (controller.context?.account_context.contact_email) {
      setReplyEmail(controller.context.account_context.contact_email);
    }
  }, [controller.context?.account_context.contact_email]);

  const validationMessage = getValidationMessage({
    category,
    description,
    replyEmail,
    subject,
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

  return (
    <div className="portal-budget-form">
      {(pane ?? "contact") === "contact" ? (
        <section className="portal-budget-form__section">
          <h3>Contact Support</h3>
          <p className="portal-budget-form__hint">
            {context.issue_reporting.honesty_notice}
          </p>
          <dl className="portal-shell__details">
            <div>
              <dt>Support email</dt>
              <dd>
                <a href={context.support_contact.support_mailto}>
                  {context.support_contact.support_email}
                </a>
              </dd>
            </div>
            <div>
              <dt>Brand</dt>
              <dd>{context.support_contact.brand_name}</dd>
            </div>
            <div>
              <dt>Homepage</dt>
              <dd>
                <a
                  href={context.support_contact.homepage_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  {context.support_contact.homepage_url}
                </a>
              </dd>
            </div>
            <div>
              <dt>Helpful links</dt>
              <dd>
                <a href={context.product_links.api_access_hash}>API access</a>
                {" | "}
                <a href={context.product_links.usage_hash}>Usage</a>
                {" | "}
                <a href={context.product_links.billing_hash}>Billing</a>
              </dd>
            </div>
          </dl>
          <p className="portal-budget-form__hint">
            {context.issue_reporting.urgent_contact_notice}
          </p>
        </section>
      ) : null}

      {(pane ?? "report") === "report" ? (
        <section className="portal-budget-form__section">
          <h3>Report An Issue</h3>
          <form className="portal-form portal-form--detail">
            <label className="portal-form__field" htmlFor="support-category">
              <span>Category</span>
              <select
                className="portal-form__input"
                id="support-category"
                onChange={(event) => {
                  controller.clearReceipt();
                  setCategory(
                    event.target
                      .value as (typeof supportCategories)[number]["value"],
                  );
                }}
                value={category}
              >
                {supportCategories.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="portal-form__field" htmlFor="support-reply-email">
              <span>Reply email</span>
              <input
                className="portal-form__input"
                id="support-reply-email"
                onChange={(event) => {
                  controller.clearReceipt();
                  setReplyEmail(event.target.value);
                }}
                placeholder="ops@example.org"
                type="email"
                value={replyEmail}
              />
            </label>

            <label className="portal-form__field" htmlFor="support-subject">
              <span>Subject</span>
              <input
                className="portal-form__input"
                id="support-subject"
                onChange={(event) => {
                  controller.clearReceipt();
                  setSubject(event.target.value);
                }}
                placeholder="Short summary of the issue"
                type="text"
                value={subject}
              />
            </label>

            <label className="portal-form__field" htmlFor="support-description">
              <span>Description</span>
              <textarea
                className="portal-form__input"
                id="support-description"
                onChange={(event) => {
                  controller.clearReceipt();
                  setDescription(event.target.value);
                }}
                placeholder="Describe the issue, what you expected, and what happened."
                rows={5}
                value={description}
              />
            </label>
          </form>

          <p className="portal-budget-form__hint">
            Requests are recorded for follow-up. Use the Recommendation category
            for constructive feedback about future capabilities.
          </p>

          {validationMessage ? (
            <p className="portal-feedback portal-feedback--error">
              {validationMessage}
            </p>
          ) : null}

          {controller.error ? (
            <p className="portal-feedback portal-feedback--error">
              {controller.error}
            </p>
          ) : null}

          {controller.receipt ? (
            <PortalNotice title="Support request sent" tone="warning">
              <p>
                Your request was sent on{" "}
                {formatDateTime(controller.receipt.submitted_at)}. We'll follow up
                through {controller.receipt.support_email}.
              </p>
            </PortalNotice>
          ) : null}

          <div className="portal-form__actions">
            <button
              className="portal-shell__action portal-shell__action--primary"
              disabled={controller.isSubmitting || validationMessage !== null}
              onClick={() => {
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
                    reply_email: replyEmail.trim() || null,
                    subject: subject.trim(),
                  })
                  .then(() => {
                    setSubject("");
                    setDescription("");
                  })
                  .catch(() => {});
              }}
              type="button"
            >
              {controller.isSubmitting
                ? "Sending support request..."
                : "Send support request"}
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function getValidationMessage(input: {
  category: string;
  description: string;
  replyEmail: string;
  subject: string;
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
  if (
    input.replyEmail.trim() &&
    !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(input.replyEmail.trim())
  ) {
    return "Reply email must be a valid email address.";
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
