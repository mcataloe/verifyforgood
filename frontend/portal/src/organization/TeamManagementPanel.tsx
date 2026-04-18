import { useEffect, useMemo, useState } from "react";
import {
  DataTable,
  Inline,
  Panel,
  type DataTableColumn,
} from "@charity-status/shared-ui";
import { PortalNotice } from "../components/feedback";
import { StackedDetailSections } from "../components/shell";
import { usePortalOrganization } from "./usePortalOrganization";
import {
  createPortalMembershipClient,
  type PortalInvitationCreateResponse,
  type PortalOrganizationInvitationSummary,
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
  const [invitations, setInvitations] = useState<PortalOrganizationInvitationSummary[]>([]);
  const [invitationsStatus, setInvitationsStatus] = useState<"idle" | "loading" | "ready">("idle");
  const [pendingRemovalMemberId, setPendingRemovalMemberId] = useState<string | null>(null);
  const [removingMemberId, setRemovingMemberId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inviteResult, setInviteResult] =
    useState<PortalInvitationCreateResponse | null>(null);

  const canManageMembers =
    organization.currentMembership?.role === "admin" &&
    organization.currentMembership?.status === "active";
  const memberColumns: DataTableColumn<(typeof organization.members)[number]>[] = [
    {
      key: "name",
      header: "Name",
      sortable: true,
      render: (member) => member.full_name ?? "Unnamed teammate",
      sortValue: (member) => member.full_name ?? member.email ?? member.user_id,
    },
    {
      key: "email",
      header: "Email",
      sortable: true,
      render: (member) => member.email ?? "Unknown email",
      sortValue: (member) => member.email ?? member.user_id,
    },
    {
      key: "role",
      header: "Role",
      sortable: true,
      render: (member) => {
        const isSelf =
          member.user_id === organization.currentMembership?.user_id;
        const isEditable = canManageMembers && !isSelf;

        return isEditable ? (
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
        );
      },
      sortValue: (member) => member.role,
    },
    {
      key: "status",
      header: "Status",
      sortable: true,
      render: (member) => member.status,
      sortValue: (member) => member.status,
    },
    {
      key: "updated_at",
      header: "Updated",
      sortable: true,
      render: (member) => formatDateTime(member.updated_at),
      sortValue: (member) => member.updated_at,
    },
    {
      key: "action",
      header: "Action",
      render: (member) => {
        const isSelf =
          member.user_id === organization.currentMembership?.user_id;
        const isEditable = canManageMembers && !isSelf;

        if (!isEditable) {
          return <span>{isSelf ? "Current user" : "Read only"}</span>;
        }

        if (pendingRemovalMemberId === member.user_id) {
          return (
            <Inline className="portal-form__actions">
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
                  : "Confirm remove"}
              </button>
              <button
                className="portal-shell__action"
                disabled={removingMemberId === member.user_id}
                onClick={() => {
                  setPendingRemovalMemberId(null);
                }}
                type="button"
              >
                Cancel
              </button>
            </Inline>
          );
        }

        return (
          <button
            className="portal-shell__action portal-shell__action--danger"
            disabled={removingMemberId === member.user_id}
            onClick={() => {
              setPendingRemovalMemberId(member.user_id);
            }}
            type="button"
          >
            Remove
          </button>
        );
      },
    },
  ];
  const invitationColumns: DataTableColumn<(typeof invitations)[number]>[] = [
    {
      key: "email",
      header: "Email",
      sortable: true,
      render: (invitation) => invitation.email,
      sortValue: (invitation) => invitation.email,
    },
    {
      key: "role",
      header: "Role",
      sortable: true,
      render: (invitation) => invitation.role,
      sortValue: (invitation) => invitation.role,
    },
    {
      key: "status",
      header: "Invitation Status",
      sortable: true,
      render: (invitation) => invitation.status,
      sortValue: (invitation) => invitation.status,
    },
    {
      key: "created_at",
      header: "Sent",
      sortable: true,
      render: (invitation) => formatDateTime(invitation.created_at),
      sortValue: (invitation) => invitation.created_at,
    },
    {
      key: "expires_at",
      header: "Expires",
      sortable: true,
      render: (invitation) => formatDateTime(invitation.expires_at),
      sortValue: (invitation) => invitation.expires_at,
    },
    {
      key: "accepted_at",
      header: "Accepted",
      sortable: true,
      render: (invitation) =>
        invitation.accepted_at
          ? formatDateTime(invitation.accepted_at)
          : "Not accepted",
      sortValue: (invitation) => invitation.accepted_at ?? "",
    },
    {
      key: "invited_by",
      header: "Invited By",
      sortable: true,
      render: (invitation) => invitation.invited_by_user_id ?? "Unknown",
      sortValue: (invitation) => invitation.invited_by_user_id ?? "",
    },
  ];

  useEffect(() => {
    let cancelled = false;

    const loadMembers = async () => {
      setIsRefreshing(true);
      setInvitationsStatus("loading");
      try {
        await Promise.all([
          organization.refreshMembers(),
          teamClient.listInvitations().then((items) => {
            if (!cancelled) {
              setInvitations(items);
            }
          }),
        ]);
        if (!cancelled) {
          setInvitationsStatus("ready");
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(
            nextError instanceof Error
              ? nextError.message
              : "Unable to load team members.",
          );
          setInvitationsStatus("ready");
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
    setInvitationsStatus("loading");
    try {
      const [, invitationItems] = await Promise.all([
        organization.refreshMembers(),
        teamClient.listInvitations(),
      ]);
      setInvitations(invitationItems);
      setInvitationsStatus("ready");
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Unable to load team members.",
      );
      setInvitationsStatus("ready");
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
      setPendingRemovalMemberId(null);
    }
  };

  return (
    <StackedDetailSections
      sectionWrapper={({ section }) => <section>{section}</section>}
    >
      <Panel
        title="Team management"
        subtitle="Invite teammates and manage access for your organization."
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
            <p>
              The invitation also appears below in the Invitations table for
              durable status tracking.
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
        title="Active members"
        subtitle="People who currently have access to this organization."
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
          <DataTable
            ariaLabel="Active organization members"
            columns={memberColumns}
            getSearchText={(member) =>
              `${member.full_name ?? ""} ${member.email ?? ""} ${member.role} ${member.status}`
            }
            initialSort={{ columnKey: "updated_at", direction: "desc" }}
            pageSize={8}
            rowKey={(member) => member.user_id}
            rows={organization.members}
            searchPlaceholder="Search members"
          />
        ) : null}
      </Panel>

      <Panel
        title="Invitations"
        subtitle="Pending, accepted, and expired invitation lifecycle records for the current organization."
      >
        {invitationsStatus === "loading" ? (
          <PortalNotice title="Loading" tone="loading">
            <p>Loading invitations for the current organization.</p>
          </PortalNotice>
        ) : null}

        {invitationsStatus !== "loading" && invitations.length === 0 ? (
          <PortalNotice title="No invitations yet" tone="empty">
            <p>The current organization has no invitation activity yet.</p>
          </PortalNotice>
        ) : null}

        {invitations.length > 0 ? (
          <DataTable
            ariaLabel="Organization invitations"
            columns={invitationColumns}
            getSearchText={(invitation) =>
              `${invitation.email} ${invitation.role} ${invitation.status} ${invitation.invited_by_user_id ?? ""}`
            }
            initialSort={{ columnKey: "created_at", direction: "desc" }}
            pageSize={8}
            rowKey={(invitation) => invitation.invitation_id}
            rows={invitations}
            searchPlaceholder="Search invitations"
          />
        ) : null}
      </Panel>
    </StackedDetailSections>
  );
}

function formatDateTime(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }

  return new Date(parsed).toLocaleString();
}
