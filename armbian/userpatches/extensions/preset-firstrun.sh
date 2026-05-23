# preset-firstrun.sh — pre-set Armbian first-run wizard values.
# Based on Armbian's built-in preset-firstrun extension pattern.
# Enable via: ENABLE_EXTENSIONS="atomicpi-profile preset-firstrun"
#
# DO NOT commit real passwords or private keys here.
# For CI builds, inject via repository secrets and environment variables.
# For personal builds, edit this file locally (do not push changes).

function config_pre_main__preset_firstrun_values() {
    # Locale and timezone
    PRESET_LOCALE="en_US.UTF-8"
    PRESET_TIMEZONE="America/Los_Angeles"

    # Default username (Armbian first-run will prompt for password if not set)
    PRESET_USER_NAME="atomicpi"
    PRESET_USER_SHELL="bash"

    # SSH public key for the user (set to your actual key or inject from CI secret)
    # PRESET_USER_KEY="ssh-ed25519 AAAA... your-key-here"

    # Root password (leave empty to force interactive set on first login)
    PRESET_ROOT_PASSWORD=""

    # Do not autologin on console — require authentication
    CONSOLE_AUTOLOGIN=no
}
