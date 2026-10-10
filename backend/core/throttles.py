from rest_framework.throttling import AnonRateThrottle


class PublicRegistrationReadThrottle(AnonRateThrottle):
    scope = 'public_registration_read'


class PublicRegistrationSubmitThrottle(AnonRateThrottle):
    scope = 'public_registration_submit'


class PublicInvitationThrottle(AnonRateThrottle):
    scope = 'public_invitation'
