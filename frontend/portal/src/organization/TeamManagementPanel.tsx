import { useEffect, useMemo, useState } from "react";
import { Grid, Inline, Panel } from "@charity-status/shared-ui";
import { PortalNotice } from "../components/feedback";
import { usePortalOrganization } from "./usePortalOrganization";
import {
  createPortalMembershipClient,
  type PortalInvitationCreateResponse,
} from "./portalMembership";

export function TeamManagementPanel() {
  const organization = usePortalOrganization();
  const teamClient = useMemo(
    () => createPortalMembershipClient(organization.apiClient),
    [organization.apiClient],
  );
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"admin" | "user">("user");
  const [isInviting, setIsInviting] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [updatingMemberId, setUpdatingMemberId] = useState<string | null>(null);
  const [removingMemberId, setRemovingMemberId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inviteResult, setInviteResult] =
    useState<PortalInvitationCreateResponse | null>(null);

  const canManageMembers =
    organization.currentMembership?.role === "admin" &&
    organization.currentMembership?.status === "active";

  useEffect(() => {
    let cancelled = false;

    const loadMembers = async () => {
      setIsRefreshing(true);
      try {
        await organization.refreshMembers();
      } catch (nextError) {
        if (!cancelled) {
          setError(
            nextError instanceof Error
              ? nextError.message
              : "Unable to load team members.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsRefreshing(false);
        }
      }
    };

    void loadMembers();

    return () => {
      cancelled = true;
    };
  }, [organization]);

  const handleRefresh = async () => {
    setError(null);
    setIsRefreshing(true);
    try {
      await organization.refreshMembers();
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Unable to load team members.",
      );
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleInvite = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canManageMembers) {
      return;
    }
    if (!inviteEmail.trim()) {
      setError("Enter an email address to invite a teammate.");
      return;
    }

    setError(null);
    setInviteResult(null);
    setIsInviting(true);
    try {
      const result = await teamClient.inviteMember({
        email: inviteEmail.trim(),
        role: inviteRole,
      });
      setInviteResult(result);
      setInviteEmail("");
      await handleRefresh();
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Unable to create invitation.",
      );
    } finally {
      setIsInviting(false);
    }
  };

  const handleRoleChange = async (
    memberId: string,
    role: "admin" | "user",
  ) => {
    setError(null);
    setUpdatingMemberId(memberId);
    try {
      const updated = await teamClient.updateMember(memberId, { role });
      organization.setMembers(
        organization.members.map((member) =>
          member.user_id === memberId ? updated : member,
        ),
      );
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Unable to update member role.",
      );
    } finally {
      setUpdatingMemberId(null);
    }
  };

  const handleRemove = async (memberId: string) => {
    setError(null);
    setRemovingMemberId(memberId);
    try {
      await teamClient.removeMember(memberId);
      organization.setMembers(
        organization.members.filter((member) => member.user_id !== memberId),
      );
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Unable to remove member.",
      );
    } finally {
      setRemovingMemberId(null);
    }
  };

  return (
    <Grid className="portal-page-grid">
      <Panel
        title="Team management"
        subtitle="Members and invitations for the current organization."
      >
        <dl className="portal-shell__details">
          <div>
            <dt>Organization</dt>
            <dd>{organization.activeOrganization.organization_name}</dd>
          </div>
          <div>
            <dt>Your role</dt>
            <dd>{organization.currentMembership?.role ?? "unknown"}</dd>
          </div>
          <div>
            <dt>Membership state</dt>
            <dd>{organization.currentMembership?.status ?? "unknown"}</dd>
          </div>
        </dl>

        {error ? (
          <PortalNotice tone="error">
            <p>{error}</p>
          </PortalNotice>
        ) : null}

        {inviteResult ? (
          <PortalNotice title="Invitation created" tone="warning">
            <p>
              Share this token with the invited user now:
              {" "}
              <code>{inviteResult.token}</code>
            </p>
          </PortalNotice>
        ) : null}

        {!canManageMembers ? (
          <PortalNotice title="Read-only team view" tone="empty">
            <p>
              Only organization admins may invite teammates or change
              membership state.
            </p>
          </PortalNotice>
        ) : (
          <form className="portal-form" onSubmit={handleInvite}>
            <label className="portal-form__field">
              <span>Invite email</span>
              <input
                className="portal-form__input"
                name="invite-email"
                onChange={(event) => setInviteEmail(event.target.value)}
                placeholder="teammate@example.org"
                type="email"
                value={inviteEmail}
              />
            </label>

            <label className="portal-form__field">
              <span>Role</span>
              <select
                className="portal-form__input"
                name="invite-role"
                onChange={(event) =>
                  setInviteRole(event.target.value as "admin" | "user")
                }
                value={inviteRole}
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </label>

            <Inline className="portal-form__actions">
              <button
                className="portal-shell__action portal-shell__action--primary"
                disabled={isInviting}
                type="submit"
              >
                {isInviting ? "Sending invite..." : "Invite user"}
              </button>
              <button
                className="portal-shell__action"
                disabled={isRefreshing}
                onClick={() => {
                  void handleRefresh();
                }}
                type="button"
              >
                {isRefreshing ? "Refreshing..." : "Refresh team"}
              </button>
            </Inline>
          </form>
        )}
      </Panel>

      <Panel
        title="Members"
        subtitle="Current organization memberships returned by the backend contract."
      >
        {organization.membersStatus === "loading" ? (
          <PortalNotice title="Loading" tone="loading">
            <p>Loading members for the current organization.</p>
          </PortalNotice>
        ) : null}

        {organization.membersStatus !== "loading" &&
        organization.members.length === 0 ? (
          <PortalNotice title="No members yet" tone="empty">
            <p>The current organization has no visible memberships yet.</p>
          </PortalNotice>
        ) : null}

        {organization.members.length > 0 ? (
          <table className="portal-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Updated</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {organization.members.map((member) => {
                const isSelf =
                  member.user_id === organization.currentMembership?.user_id;
                const isEditable = canManageMembers && !isSelf;
                return (
                  <tr key={member.user_id}>
                    <td>{member.full_name ?? "Unnamed teammate"}</td>
                    <td>{member.email ?? "Unknown email"}</td>
                    <td>
                      {isEditable ? (
                        <select
                          aria-label={`Role for ${member.email ?? member.user_id}`}
                          className="portal-form__input"
                          disabled={updatingMemberId === member.user_id}
                          onChange={(event) =>
                            void handleRoleChange(
                              member.user_id,
                              event.target.value as "admin" | "user",
                            )
                          }
                          value={member.role}
                        >
                          <option value="user">User</option>
                          <option value="admin">Admin</option>
                        </select>
                      ) : (
                        <span>{member.role}</span>
                      )}
                    </td>
                    <td>{member.status}</td>
                    <td>{formatDateTime(member.updated_at)}</td>
                    <td>
                      {isEditable ? (
                        <button
                          className="portal-shell__action portal-shell__action--danger"
                          disabled={removingMemberId === member.user_id}
                          onClick={() => {
                            void handleRemove(member.user_id);
                          }}
                          type="button"
                        >
                          {removingMemberId === member.user_id
                            ? "Removing..."
                            : "Remove"}
                        </button>
                      ) : isSelf ? (
                        <span>Current user</span>
                      ) : (
                        <span>Read only</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : null}
      </Panel>
    </Grid>
  );
}

function formatDateTime(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }

  return new Date(parsed).toLocaleString();
}
