import { useMemo, useState } from "react";
import {
  Avatar,
  FileInput,
  NativeSelect,
  Stack,
  TextInput,
} from "@mantine/core";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import {
  PortalDetailSection,
  PortalDetailView,
} from "../components/PortalDetailView";
import {
  PortalActionGroup,
  PortalButton,
  PortalHint,
} from "../components/PortalPrimitives";
import { PortalNotice } from "../components/feedback";
import { AppearancePreferenceSection } from "../settings/AppearancePreferenceSection";

interface CustomerUserProfilePageProps {
  environment: string;
  session: PortalAuthenticatedSession;
}

export function CustomerUserProfilePage({
  environment: _environment,
  session,
}: CustomerUserProfilePageProps) {
  const [savedPersonalInfo, setSavedPersonalInfo] = useState(() =>
    loadStoredPersonalInfo(
      session.user.subject_id,
      session.user.display_name,
      session.user.email,
    ),
  );
  const [firstName, setFirstName] = useState(savedPersonalInfo.firstName);
  const [lastName, setLastName] = useState(savedPersonalInfo.lastName);
  const [email, setEmail] = useState(savedPersonalInfo.email);
  const [pronouns, setPronouns] = useState(savedPersonalInfo.pronouns);
  const [personalInfoNotice, setPersonalInfoNotice] = useState<string | null>(null);
  const [avatarDraft, setAvatarDraft] = useState<File | null>(null);
  const [savedAvatar, setSavedAvatar] = useState<StoredAvatar | null>(() =>
    loadStoredAvatar(session.user.subject_id),
  );
  const [avatarNotice, setAvatarNotice] = useState<string | null>(null);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const initials = useMemo(
    () =>
      `${firstName[0] ?? ""}${lastName[0] ?? ""}`.trim().toUpperCase() || "VF",
    [firstName, lastName],
  );
  const trimmedFirstName = firstName.trim();
  const trimmedLastName = lastName.trim();
  const trimmedEmail = email.trim();
  const isPersonalInfoDirty =
    trimmedFirstName !== savedPersonalInfo.firstName ||
    trimmedLastName !== savedPersonalInfo.lastName ||
    trimmedEmail !== savedPersonalInfo.email ||
    pronouns !== savedPersonalInfo.pronouns;
  const personalInfoValidationMessage = getPersonalInfoValidationMessage({
    email: trimmedEmail,
    firstName: trimmedFirstName,
    lastName: trimmedLastName,
  });

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
              setPersonalInfoNotice(null);
              setFirstName(event.target.value);
            }}
            value={firstName}
          />

          <TextInput
            aria-label="Last Name"
            label="Last Name"
            onChange={(event) => {
              setPersonalInfoNotice(null);
              setLastName(event.target.value);
            }}
            value={lastName}
          />

          <TextInput
            aria-label="Email"
            label="Email"
            onChange={(event) => {
              setPersonalInfoNotice(null);
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
              setPersonalInfoNotice(null);
              setPronouns(event.currentTarget.value || "Prefer not to say");
            }}
            value={pronouns}
          />

          {personalInfoValidationMessage ? (
            <PortalNotice tone="error">
              <p>{personalInfoValidationMessage}</p>
            </PortalNotice>
          ) : null}

          {personalInfoNotice ? (
            <PortalNotice title="Saved" tone="warning">
              <p>{personalInfoNotice}</p>
            </PortalNotice>
          ) : null}

          <PortalActionGroup>
            <PortalButton
              disabled={
                !isPersonalInfoDirty || personalInfoValidationMessage !== null
              }
              onClick={() => {
                if (!isPersonalInfoDirty || personalInfoValidationMessage) {
                  return;
                }

                const nextPersonalInfo = {
                  email: trimmedEmail,
                  firstName: trimmedFirstName,
                  lastName: trimmedLastName,
                  pronouns,
                };
                storePersonalInfo(session.user.subject_id, nextPersonalInfo);
                setSavedPersonalInfo(nextPersonalInfo);
                setPersonalInfoNotice("Profile details saved on this device.");
              }}
              tone="primary"
              type="button"
            >
              Save
            </PortalButton>
          </PortalActionGroup>
        </Stack>
      </PortalDetailSection>

      <PortalDetailSection
        intro="Choose the image you want to use for your profile."
        title="Avatar"
      >
        <Stack gap="md" maw={540}>
          <Avatar
            color="dark"
            radius="xl"
            size={72}
            src={savedAvatar?.dataUrl ?? undefined}
          >
            {initials}
          </Avatar>
          <FileInput
            aria-label="Avatar upload"
            clearable
            label="Avatar upload"
            onChange={(file) => {
              setAvatarError(null);
              setAvatarNotice(null);
              setAvatarDraft(file);
            }}
            placeholder="Choose an image"
            value={avatarDraft}
          />
          <PortalHint>
            {avatarDraft
              ? `Selected file: ${avatarDraft.name}`
              : savedAvatar?.name
                ? `Saved avatar: ${savedAvatar.name}`
                : "No file selected"}
          </PortalHint>

          {avatarError ? (
            <PortalNotice tone="error">
              <p>{avatarError}</p>
            </PortalNotice>
          ) : null}

          {avatarNotice ? (
            <PortalNotice title="Saved" tone="warning">
              <p>{avatarNotice}</p>
            </PortalNotice>
          ) : null}

          <PortalActionGroup>
            <PortalButton
              disabled={!avatarDraft}
              onClick={() => {
                if (!avatarDraft) {
                  return;
                }

                void readFileAsDataUrl(avatarDraft).then((dataUrl) => {
                  const nextAvatar = {
                    dataUrl,
                    name: avatarDraft.name,
                  };
                  storeAvatar(session.user.subject_id, nextAvatar);
                  setSavedAvatar(nextAvatar);
                  setAvatarDraft(null);
                  setAvatarNotice("Avatar saved on this device.");
                }).catch(() => {
                  setAvatarError("Avatar could not be saved on this device.");
                });
              }}
              tone="primary"
              type="button"
            >
              Save
            </PortalButton>
          </PortalActionGroup>
        </Stack>
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

type StoredPersonalInfo = {
  email: string;
  firstName: string;
  lastName: string;
  pronouns: string;
};

type StoredAvatar = {
  dataUrl: string;
  name: string;
};

const PROFILE_STORAGE_KEY_PREFIX = "verifyforgood.portal.profile";
const AVATAR_STORAGE_KEY_PREFIX = "verifyforgood.portal.avatar";

function getPersonalInfoValidationMessage(input: {
  email: string;
  firstName: string;
  lastName: string;
}) {
  if (input.firstName.length < 1) {
    return "First name is required.";
  }

  if (input.lastName.length < 1) {
    return "Last name is required.";
  }

  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(input.email)) {
    return "Email must be a valid email address.";
  }

  return null;
}

function loadStoredPersonalInfo(
  subjectId: string,
  displayName: string,
  email: string,
): StoredPersonalInfo {
  const fallbackName = splitDisplayName(displayName);
  const fallback: StoredPersonalInfo = {
    email,
    firstName: fallbackName.firstName,
    lastName: fallbackName.lastName,
    pronouns: "Prefer not to say",
  };
  const storage = resolveStorage();

  if (!storage) {
    return fallback;
  }

  try {
    const raw = storage.getItem(`${PROFILE_STORAGE_KEY_PREFIX}:${subjectId}`);
    if (!raw) {
      return fallback;
    }

    const parsed = JSON.parse(raw) as Partial<StoredPersonalInfo>;
    return {
      email: parsed.email?.trim() || fallback.email,
      firstName: parsed.firstName?.trim() || fallback.firstName,
      lastName: parsed.lastName?.trim() || fallback.lastName,
      pronouns: parsed.pronouns?.trim() || fallback.pronouns,
    };
  } catch {
    return fallback;
  }
}

function storePersonalInfo(subjectId: string, value: StoredPersonalInfo) {
  const storage = resolveStorage();
  if (!storage) {
    return;
  }

  storage.setItem(
    `${PROFILE_STORAGE_KEY_PREFIX}:${subjectId}`,
    JSON.stringify(value),
  );
}

function loadStoredAvatar(subjectId: string): StoredAvatar | null {
  const storage = resolveStorage();
  if (!storage) {
    return null;
  }

  try {
    const raw = storage.getItem(`${AVATAR_STORAGE_KEY_PREFIX}:${subjectId}`);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as Partial<StoredAvatar>;
    if (!parsed.name || !parsed.dataUrl) {
      return null;
    }

    return {
      dataUrl: parsed.dataUrl,
      name: parsed.name,
    };
  } catch {
    return null;
  }
}

function storeAvatar(subjectId: string, value: StoredAvatar) {
  const storage = resolveStorage();
  if (!storage) {
    return;
  }

  storage.setItem(
    `${AVATAR_STORAGE_KEY_PREFIX}:${subjectId}`,
    JSON.stringify(value),
  );
}

function resolveStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage;
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onerror = () => {
      reject(new Error("Avatar preview could not be read."));
    };
    reader.onload = () => {
      if (typeof reader.result !== "string") {
        reject(new Error("Avatar preview could not be read."));
        return;
      }

      resolve(reader.result);
    };

    reader.readAsDataURL(file);
  });
}
