import { Button, Group, Modal, Stack, Text } from "@mantine/core";
import { useEffect, useState } from "react";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { PortalOrganizationDeletionController } from "./usePortalOrganizationDeletion";

interface OrganizationDeletionPanelProps {
  controller: PortalOrganizationDeletionController;
  session: PortalAuthenticatedSession;
}

export function OrganizationDeletionPanel({
  controller,
  session,
}: OrganizationDeletionPanelProps) {
  const [confirmationSlug, setConfirmationSlug] = useState("");
  const [opened, setOpened] = useState(false);

  useEffect(() => {
    if (!opened) {
      setConfirmationSlug("");
    }
  }, [opened]);

  const expectedSlug = controller.organizationSlug ?? "";
  const canDelete =
    !controller.isDeleting &&
    expectedSlug.length > 0 &&
    confirmationSlug.trim().toLowerCase() === expectedSlug.toLowerCase();

  return (
    <>
      <div className="portal-budget-form">
        <p className="portal-budget-form__hint">
          Delete this organization if it should no longer appear in the portal.
          Its history remains available for audit purposes.
        </p>

        <div className="portal-form__actions">
          <button
            className="portal-shell__action portal-shell__action--danger"
            onClick={() => {
              setOpened(true);
            }}
            type="button"
          >
            Delete Organization
          </button>
        </div>
      </div>

      <Modal
        centered
        onClose={() => {
          setOpened(false);
        }}
        opened={opened}
        title="Delete Organization"
      >
        <Stack gap="md">
          <Text size="sm">
            You are deleting <strong>{controller.organizationName}</strong>.
            This action will be recorded as performed by{" "}
            <strong>{session.user.display_name}</strong>.
          </Text>
          <Text size="sm">
            To confirm, type this organization slug exactly:
          </Text>
          <Text fw={700} size="sm">
            {expectedSlug || "Slug unavailable"}
          </Text>
          <label className="portal-form__field" htmlFor="delete-organization-slug">
            <span>Organization slug</span>
            <input
              className="portal-form__input"
              id="delete-organization-slug"
              onChange={(event) => {
                setConfirmationSlug(event.target.value);
              }}
              type="text"
              value={confirmationSlug}
            />
          </label>

          {controller.error ? (
            <p className="portal-feedback portal-feedback--error">
              {controller.error}
            </p>
          ) : null}

          <Group justify="flex-end">
            <Button
              onClick={() => {
                setOpened(false);
              }}
              variant="default"
            >
              Cancel
            </Button>
            <Button
              color="red"
              disabled={!canDelete}
              onClick={() => {
                void controller.deleteOrganization({
                  slug: confirmationSlug.trim(),
                }).then((wasDeleted) => {
                  if (wasDeleted) {
                    setOpened(false);
                  }
                });
              }}
            >
              {controller.isDeleting ? "Deleting..." : "Delete Organization"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
