"""Onboarding submission endpoint.

Receives user onboarding selections and fires analytics event.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from openhands.server.user_auth import get_user_id

onboarding_router = APIRouter(prefix='/api', tags=['Onboarding'])


class OnboardingSubmission(BaseModel):
    selections: dict[str, str]  # step_id -> option_id (e.g., {"step1": "software_engineer", "step2": "solo", "step3": "new_features"})


class OnboardingResponse(BaseModel):
    status: str
    redirect_url: str


@onboarding_router.post('/onboarding', response_model=OnboardingResponse)
async def submit_onboarding(
    body: OnboardingSubmission,
    user_id: str | None = Depends(get_user_id),
) -> OnboardingResponse:
    """Submit onboarding form selections and fire analytics event."""
    # ACTV-03: onboarding completed
    try:
        from openhands.analytics import analytics_constants, get_analytics_service

        analytics = get_analytics_service()
        if analytics and user_id:
            from enterprise.storage.user_store import UserStore

            user_obj = await UserStore.get_user_by_id_async(user_id)
            if user_obj:
                consented = user_obj.user_consents_to_analytics is True
                org_id_str = str(user_obj.current_org_id) if user_obj.current_org_id else None
                analytics.capture(
                    distinct_id=user_id,
                    event=analytics_constants.ONBOARDING_COMPLETED,
                    properties={
                        'role': body.selections.get('step1'),
                        'org_size': body.selections.get('step2'),
                        'use_case': body.selections.get('step3'),
                    },
                    org_id=org_id_str,
                    consented=consented,
                )
                # Associate onboarding timestamp with org group
                if org_id_str:
                    analytics.group_identify(
                        group_type='org',
                        group_key=org_id_str,
                        properties={
                            'onboarding_completed_at': datetime.now(timezone.utc).isoformat(),
                        },
                        distinct_id=user_id,
                        consented=consented,
                    )
    except Exception:
        import logging
        logging.getLogger(__name__).exception('analytics:onboarding_completed:failed')

    return OnboardingResponse(status='ok', redirect_url='/')
