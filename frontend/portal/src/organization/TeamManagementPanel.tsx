import { useEffect, useMemo, useState } from "react";
import {
  ActionIcon,
  Group,
  Modal,
  NativeSelect,
  Stack,
  Tabs,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { IconEdit, IconTrash } from "@tabler/icons-react";
import {
  DataTable,
  Panel,
  type DataTableColumn,
} from "@charity-status/shared-ui";
import {
  PortalActionGroup,
  PortalButton,
} from "../components/PortalPrimitives";
import { PortalNotice } from "../components/feedback";
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
  const inviterNameByUserId = useMemo(() => {
    return new Map(
      organization.members
        .filter((member) => member.user_id)
        .map((member) => [
          member.user_id,
          member.full_name ?? member.email ?? member.user_id,
        ]),
    );
  }, [organization.members]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"admin" | "user">("user");
  const [isInviting, setIsInviting] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [updatingMemberId, setUpdatingMemberId] = useState<string | null>(null);
  const [invitations, setInvitations] = useState<PortalOrganizationInvitationSummary[]>([]);
  const [invitationsStatus, setInvitationsStatus] = useState<"idle" | "loading" | "ready">("idle");
  const [editingMember, setEditingMember] = useState<
    (typeof organization.members)[number] | null
  >(null);
  const [editingRole, setEditingRole] = useState<"admin" | "user">("user");
  const [pendingRemovalMember, setPendingRemovalMember] = useState<
    (typeof organization.members)[number] | null
  >(null);
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
      render: (member) => formatLabelValue(member.role),
      sortValue: (member) => member.role,
    },
    {
      key: "status",
      header: "Status",
      sortable: true,
      render: (member) => formatLabelValue(member.status),
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

        const isUpdating = updatingMemberId === member.user_id;
        const isRemoving = removingMemberId === member.user_id;

        return (
          <Group gap="xs" wrap="nowrap">
            <Tooltip label="Edit member" withArrow withinPortal>
              <ActionIcon
                aria-label={`Edit member ${member.email ?? member.user_id}`}
                color="gray"
                disabled={isUpdating || isRemoving}
                onClick={() => {
                  setEditingMember(member);
                  setEditingRole(normalizeMemberRole(member.role));
                }}
                radius="xl"
                size="lg"
                type="button"
                variant="subtle"
              >
                <IconEdit aria-hidden="true" size={16} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Delete member" withArrow withinPortal>
              <ActionIcon
                aria-label={`Delete member ${member.email ?? member.user_id}`}
                color="red"
                disabled={isUpdating || isRemoving}
                onClick={() => {
                  setPendingRemovalMember(member);
                }}
                radius="xl"
                size="lg"
                type="button"
                variant="subtle"
              >
                <IconTrash aria-hidden="true" size={16} />
              </ActionIcon>
            </Tooltip>
          </Group>
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
      render: (invitation) => formatDate(invitation.created_at),
      sortValue: (invitation) => invitation.created_at,
    },
    {
      key: "expires_at",
      header: "Expires",
      sortable: true,
      render: (invitation) => formatDate(invitation.expires_at),
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
      render: (invitation) =>
        formatInviterName(invitation.invited_by_user_id, inviterNameByUserId),
      sortValue: (invitation) =>
        formatInviterName(invitation.invited_by_user_id, inviterNameByUserId),
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
  }, [organization.refreshMembers, teamClient]);

  useEffect(() => {
    setEditingRole(normalizeMemberRole(editingMember?.role));
  }, [editingMember]);

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
      return true;
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Unable to update member role.",
      );
      return false;
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
      setPendingRemovalMember(null);
      return true;
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Unable to remove member.",
      );
      return false;
    } finally {
      setRemovingMemberId(null);
    }
  };

  return (
    <>
      <Tabs color="primary" defaultValue="team-management" variant="outline">
        <Tabs.List aria-label="Team sections">
          <Tabs.Tab value="team-management">Team Management</Tabs.Tab>
          <Tabs.Tab value="active-members">Active Members</Tabs.Tab>
          <Tabs.Tab value="invitations">Invitations</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel pt="md" value="team-management">
          <Panel
            title="Team management"
            subtitle="Invite teammates and manage access for your organization."
          >
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
              <form onSubmit={handleInvite}>
                <Stack gap="md">
                  <TextInput
                    label="Invite email"
                    name="invite-email"
                    onChange={(event) => setInviteEmail(event.currentTarget.value)}
                    placeholder="teammate@example.org"
                    type="email"
                    value={inviteEmail}
                  />

                  <NativeSelect
                    data={[
                      { label: "User", value: "user" },
                      { label: "Admin", value: "admin" },
                    ]}
                    label="Role"
                    name="invite-role"
                    onChange={(event) => {
                      setInviteRole(normalizeMemberRole(event.currentTarget.value));
                    }}
                    value={inviteRole}
                  />

                  <PortalActionGroup>
                    <PortalButton loading={isInviting} tone="primary" type="submit">
                      Invite user
                    </PortalButton>
                    <PortalButton
                      disabled={isRefreshing}
                      onClick={() => {
                        void handleRefresh();
                      }}
                      tone="secondary"
                      type="button"
                    >
                      {isRefreshing ? "Refreshing..." : "Refresh"}
                    </PortalButton>
                  </PortalActionGroup>
                </Stack>
              </form>
            )}
          </Panel>
        </Tabs.Panel>

        <Tabs.Panel pt="md" value="active-members">
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
        </Tabs.Panel>

        <Tabs.Panel pt="md" value="invitations">
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
        </Tabs.Panel>
      </Tabs>

      <Modal
        centered
        onClose={() => {
          setEditingMember(null);
        }}
        opened={Boolean(editingMember)}
        title="Edit Member"
      >
        <Stack>
          <Text>
            {editingMember
              ? `Update access for ${editingMember.full_name ?? editingMember.email ?? editingMember.user_id}.`
              : ""}
          </Text>
          <NativeSelect
            data={[
              { label: "User", value: "user" },
              { label: "Admin", value: "admin" },
            ]}
            disabled={!editingMember || updatingMemberId === editingMember.user_id}
            label="Role"
            onChange={(event) => {
              setEditingRole(
                normalizeMemberRole(event.currentTarget.value),
              );
            }}
            value={editingRole}
          />
          <Group justify="flex-end">
            <PortalButton
              onClick={() => {
                setEditingMember(null);
              }}
              tone="secondary"
              type="button"
            >
              Cancel
            </PortalButton>
            <PortalButton
              disabled={!editingMember || updatingMemberId === editingMember.user_id}
              onClick={() => {
                if (!editingMember) {
                  return;
                }

                void handleRoleChange(editingMember.user_id, editingRole).then(
                  (didUpdate) => {
                    if (didUpdate) {
                      setEditingMember(null);
                    }
                  },
                );
              }}
              tone="primary"
              type="button"
            >
              {editingMember && updatingMemberId === editingMember.user_id
                ? "Saving..."
                : "Save"}
            </PortalButton>
          </Group>
        </Stack>
      </Modal>

      <Modal
        centered
        onClose={() => {
          setPendingRemovalMember(null);
        }}
        opened={Boolean(pendingRemovalMember)}
        title="Delete Member"
      >
        <Stack>
          <Text>
            {pendingRemovalMember
              ? `Remove ${pendingRemovalMember.full_name ?? pendingRemovalMember.email ?? pendingRemovalMember.user_id} from ${organization.activeOrganization.organization_name}?`
              : ""}
          </Text>
          <Group justify="flex-end">
            <PortalButton
              onClick={() => {
                setPendingRemovalMember(null);
              }}
              tone="secondary"
              type="button"
            >
              Cancel
            </PortalButton>
            <PortalButton
              disabled={
                !pendingRemovalMember ||
                removingMemberId === pendingRemovalMember.user_id
              }
              onClick={() => {
                if (!pendingRemovalMember) {
                  return;
                }
                void handleRemove(pendingRemovalMember.user_id);
              }}
              tone="danger"
              type="button"
            >
              {pendingRemovalMember &&
              removingMemberId === pendingRemovalMember.user_id
                ? "Deleting..."
                : "Delete"}
            </PortalButton>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}

function formatDateTime(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }

  return new Date(parsed).toLocaleString();
}

function formatDate(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
  }).format(new Date(parsed));
}

function formatLabelValue(value: string | null | undefined) {
  const candidate = String(value ?? "").trim();
  if (!candidate) {
    return "Unknown";
  }

  return candidate
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((segment) => segment[0].toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
}

function normalizeMemberRole(value: string | null | undefined): "admin" | "user" {
  return value === "admin" ? "admin" : "user";
}

function formatInviterName(
  invitedByUserId: string | null,
  inviterNameByUserId: ReadonlyMap<string, string>,
) {
  if (!invitedByUserId) {
    return "Unknown";
  }

  return inviterNameByUserId.get(invitedByUserId) ?? invitedByUserId;
}
