import React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useUnifiedResumeConversationSandbox } from "#/hooks/mutation/use-unified-start-conversation";
import { useUserProviders } from "#/hooks/use-user-providers";
import { useErrorMessageStore } from "#/stores/error-message-store";
import { I18nKey } from "#/i18n/declaration";

const MAX_RECOVERY_ATTEMPTS = 3;
const RECOVERY_COOLDOWN_MS = 5000;
const RECOVERY_SETTLED_DELAY_MS = 2000;

/**
 * Hook that handles sandbox recovery when a stopped sandbox needs to be resumed.
 *
 * Recovery is triggered in two scenarios:
 * 1. When the user focuses on the tab after it has lost focus (visibility change)
 * 2. When the user refreshes the page (handled by conversation.tsx auto-start logic)
 *
 * NOTE: We do NOT automatically resume when WebSocket disconnects. This is intentional
 * because the server pauses sandboxes after 20 minutes of inactivity, and we should
 * only resume when the user explicitly shows intent (by focusing on the tab or refreshing).
 *
 * @param conversationId - The conversation ID to recover
 * @returns reconnectKey - Key to force provider remount (resets connection state)
 * @returns handleDisconnect - Callback to trigger recovery on WebSocket disconnect (no longer auto-resumes)
 */
export function useWebSocketRecovery(conversationId: string) {
  // Recovery state (refs to avoid re-renders)
  const recoveryAttemptsRef = React.useRef(0);
  const recoveryInProgressRef = React.useRef(false);
  const lastRecoveryAttemptRef = React.useRef<number | null>(null);

  // Key to force remount of provider after recovery (resets connection state to "CONNECTING")
  const [reconnectKey, setReconnectKey] = React.useState(0);

  const queryClient = useQueryClient();
  const { mutate: resumeConversation } = useUnifiedResumeConversationSandbox();
  const { providers } = useUserProviders();
  const setErrorMessage = useErrorMessageStore(
    (state) => state.setErrorMessage,
  );

  // Fetch conversation status to check if sandbox is stopped
  const { data: conversation } = useQuery({
    queryKey: ["user", "conversation", conversationId],
    select: (data) => data as { status: string } | undefined,
  });

  // Reset recovery state when conversation changes
  React.useEffect(() => {
    recoveryAttemptsRef.current = 0;
    recoveryInProgressRef.current = false;
    lastRecoveryAttemptRef.current = null;
  }, [conversationId]);

  // Handle visibility change - resume sandbox when tab gains focus
  // This handles the case where the sandbox was paused due to inactivity
  React.useEffect(() => {
    const handleVisibilityChange = () => {
      // Only handle when tab becomes visible (gains focus)
      if (document.visibilityState !== "visible") return;

      // Check if conversation is stopped and needs to be resumed
      if (
        conversation?.status === "STOPPED" &&
        !recoveryInProgressRef.current
      ) {
        // Prevent concurrent recovery attempts
        if (recoveryInProgressRef.current) return;

        // Check cooldown
        const now = Date.now();
        if (
          lastRecoveryAttemptRef.current &&
          now - lastRecoveryAttemptRef.current < RECOVERY_COOLDOWN_MS
        ) {
          return;
        }

        // Check max attempts - notify user when recovery is exhausted
        if (recoveryAttemptsRef.current >= MAX_RECOVERY_ATTEMPTS) {
          setErrorMessage(I18nKey.STATUS$CONNECTION_LOST);
          return;
        }

        // Start recovery
        recoveryInProgressRef.current = true;
        lastRecoveryAttemptRef.current = now;
        recoveryAttemptsRef.current += 1;

        resumeConversation(
          { conversationId, providers },
          {
            onSuccess: async () => {
              // Invalidate and wait for refetch to complete before remounting
              // This ensures the provider remounts with fresh data (url: null during startup)
              await queryClient.invalidateQueries({
                queryKey: ["user", "conversation", conversationId],
              });

              // Force remount to reset connection state to "CONNECTING"
              setReconnectKey((k) => k + 1);

              // Reset recovery state on success
              recoveryAttemptsRef.current = 0;
              recoveryInProgressRef.current = false;
              lastRecoveryAttemptRef.current = null;
            },
            onError: () => {
              // If this was the last attempt, show error to user
              if (recoveryAttemptsRef.current >= MAX_RECOVERY_ATTEMPTS) {
                setErrorMessage(I18nKey.STATUS$CONNECTION_LOST);
              }
            },
            onSettled: () => {
              // Allow next attempt after a delay (covers both success and error)
              setTimeout(() => {
                recoveryInProgressRef.current = false;
              }, RECOVERY_SETTLED_DELAY_MS);
            },
          },
        );
      }
    };

    // Add visibility change listener
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [
    conversation?.status,
    conversationId,
    providers,
    resumeConversation,
    queryClient,
    setErrorMessage,
  ]);

  // Legacy disconnect handler - no longer automatically resumes sandbox
  // Kept for backward compatibility but does nothing
  const handleDisconnect = React.useCallback(() => {
    // Intentionally empty - we no longer auto-resume on WebSocket disconnect
    // Recovery now only happens via:
    // 1. Visibility change (tab gains focus) - handled above
    // 2. Page refresh - handled by conversation.tsx auto-start logic
  }, []);

  return { reconnectKey, handleDisconnect };
}
