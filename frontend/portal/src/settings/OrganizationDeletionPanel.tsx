import { Button, Group, Modal, Stack, Text, TextInput } from "@mantine/core";
import { useEffect, useState } from "react";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import {
  PortalActionGroup,
  PortalButton,
  PortalHint,
} from "../components/PortalPrimitives";
import { PortalNotice } from "../components/feedback";
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
      <Stack gap="md">
        <PortalHint>
          Delete this organization if it should no longer appear in the portal.
          Its history remains available for audit purposes.
        </PortalHint>

        <PortalActionGroup>
          <PortalButton
            onClick={() => {
              setOpened(true);
            }}
            tone="danger"
            type="button"
          >
            Delete Organization
          </PortalButton>
        </PortalActionGroup>
      </Stack>

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
          <Text fw={700} size="sm">
            {expectedSlug || "Slug unavailable"}
          </Text>
          <TextInput
              label="Organization slug"
              id="delete-organization-slug"
              onChange={(event) => {
                setConfirmationSlug(event.target.value);
              }}
              value={confirmationSlug}
            />

          {controller.error ? (
            <PortalNotice tone="error">
              <p>{controller.error}</p>
            </PortalNotice>
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
              loading={controller.isDeleting}
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
