import { useMemo, useState } from "react";
import {
  Avatar,
  FileInput,
  NativeSelect,
  Paper,
  Stack,
  TextInput,
} from "@mantine/core";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import {
  PortalDetailSection,
  PortalDetailView,
} from "../components/PortalDetailView";
import { PortalHint } from "../components/PortalPrimitives";
import { AppearancePreferenceSection } from "../settings/AppearancePreferenceSection";

interface CustomerUserProfilePageProps {
  environment: string;
  session: PortalAuthenticatedSession;
}

export function CustomerUserProfilePage({
  environment: _environment,
  session,
}: CustomerUserProfilePageProps) {
  const [firstName, setFirstName] = useState(
    splitDisplayName(session.user.display_name).firstName,
  );
  const [lastName, setLastName] = useState(
    splitDisplayName(session.user.display_name).lastName,
  );
  const [email, setEmail] = useState(session.user.email);
  const [pronouns, setPronouns] = useState("Prefer not to say");
  const [avatarName, setAvatarName] = useState<string | null>(null);
  const initials = useMemo(
    () =>
      `${firstName[0] ?? ""}${lastName[0] ?? ""}`.trim().toUpperCase() || "VF",
    [firstName, lastName],
  );

  return (
    <PortalDetailView
      eyebrow="Profile"
      intro="Manage your profile details and appearance preferences."
      title="Profile"
    >
      <PortalDetailSection
        intro="Update the personal details shown in your profile."
        title="Personal information"
      >
        <Stack maw={540}>
          <TextInput
            aria-label="First Name"
            label="First Name"
            onChange={(event) => {
              setFirstName(event.target.value);
            }}
            value={firstName}
          />

          <TextInput
            aria-label="Last Name"
            label="Last Name"
            onChange={(event) => {
              setLastName(event.target.value);
            }}
            value={lastName}
          />

          <TextInput
            aria-label="Email"
            label="Email"
            onChange={(event) => {
              setEmail(event.target.value);
            }}
            type="email"
            value={email}
          />

          <NativeSelect
            aria-label="Pronouns"
            data={[
              "Prefer not to say",
              "She / her",
              "He / him",
              "They / them",
              "Custom / ask me",
            ]}
            label="Pronouns"
            onChange={(event) => {
              setPronouns(event.currentTarget.value || "Prefer not to say");
            }}
            value={pronouns}
          />
        </Stack>
      </PortalDetailSection>

      <PortalDetailSection
        intro="Choose the image you want to use for your profile."
        title="Avatar"
      >
        <Paper p="lg" radius="lg" withBorder>
          <Stack gap="md" maw={540}>
            <Avatar color="dark" radius="xl" size={72}>
              {initials}
            </Avatar>
            <FileInput
              aria-label="Avatar upload"
              clearable
              label="Avatar upload"
              onChange={(file) => {
                setAvatarName(file?.name ?? null);
              }}
              placeholder="Choose an image"
            />
            <PortalHint>
              {avatarName ? `Selected file: ${avatarName}` : "No file selected"}
            </PortalHint>
          </Stack>
        </Paper>
      </PortalDetailSection>

      <PortalDetailSection
        intro="Choose the appearance that feels best for you."
        title="Appearance"
      >
        <AppearancePreferenceSection showTitle={false} />
      </PortalDetailSection>
    </PortalDetailView>
  );
}

function splitDisplayName(displayName: string) {
  const [firstName = "", ...rest] = displayName.trim().split(/\s+/);

  return {
    firstName,
    lastName: rest.join(" "),
  };
}
