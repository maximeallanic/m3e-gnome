# GNOME icon name  ->  Material Symbols (style chosen in build.py: rounded, filled by default). "!" = filled variant (fill1).
M = {}
def m(names, ms):
    for n in names.split(): M[n + '-symbolic'] = ms
# Levels of one family are framed on the complete symbol, so the lone arc of weak Wi-Fi or a single cellular bar
# keeps its place and size instead of being enlarged to fill the frame.
FAMILY = {'!wifi_2_bar': '!wifi', '!wifi_1_bar': '!wifi',
           '!signal_cellular_alt_2_bar': '!signal_cellular_alt', '!signal_cellular_alt_1_bar': '!signal_cellular_alt',
           '!volume_down': '!volume_up', '!volume_mute': '!volume_up'}
# Partial levels are drawn over the complete symbol at low opacity, like Android's status bar (the inactive arcs /
# bars stay visible in grey). Material only ships the active part, so build.py adds the underlay (see UNDERLAY_OPACITY).
UNDERLAY = {v: base for v, base in FAMILY.items() if v.startswith(('!wifi', '!signal_cellular'))}
UNDERLAY_OPACITY = 0.3
# Wi-Fi: arcs and dot, as in the Android 17 status bar
m('network-wireless-signal-excellent network-wireless-connected network-wireless network-wireless-encrypted', '!wifi')
m('network-wireless-signal-good', '!wifi')
m('network-wireless-signal-ok', '!wifi_2_bar')
m('network-wireless-signal-weak', '!wifi_1_bar')
m('network-wireless-signal-none', '!signal_wifi_0_bar')
m('network-wireless-acquiring', '!wifi_find')
m('network-wireless-no-route network-wireless-offline', '!signal_wifi_bad')
m('network-wireless-disabled', '!signal_wifi_off')
m('network-wireless-hotspot', '!wifi_tethering')
# Wired, VPN, network
m('network-wired network-wired-acquiring', '!lan')
m('network-wired-disconnected network-wired-no-route network-offline network-error', '!signal_disconnected')
m('network-vpn network-vpn-acquiring', '!vpn_key')
m('network-vpn-disabled', '!vpn_key_off')
m('network-workgroup', '!lan')
# Cellular network
# separate bars, as in Android 17
m('network-cellular-signal-excellent network-cellular-connected network-cellular', '!signal_cellular_alt')
m('network-cellular-signal-good', '!signal_cellular_alt')
m('network-cellular-signal-ok', '!signal_cellular_alt_2_bar')
m('network-cellular-signal-weak', '!signal_cellular_alt_1_bar')
m('network-cellular-signal-none network-cellular-acquiring', '!signal_cellular_0_bar')
m('network-cellular-disabled network-cellular-offline', '!signal_cellular_off')
# Bluetooth
m('bluetooth-active', '!bluetooth')
m('bluetooth-acquiring', '!bluetooth_searching')
m('bluetooth-disabled', '!bluetooth_disabled')
m('bluetooth-connected', '!bluetooth_connected')
# Sound
m('audio-volume-high audio-volume-overamplified', '!volume_up')
m('audio-volume-medium', '!volume_down')
m('audio-volume-low', '!volume_mute')
m('audio-volume-muted', '!volume_off')
m('audio-headphones', '!headphones')
m('audio-headset', '!headset_mic')
m('audio-speakers', '!speaker')
# Microphone
m('microphone-sensitivity-high microphone-sensitivity-medium microphone-sensitivity-low audio-input-microphone', '!mic')
m('microphone-sensitivity-muted microphone-disabled', '!mic_off')
# Battery: Android 16 horizontal model (battery_android_*)
lv = {0:'battery_android_0',10:'battery_android_1',20:'battery_android_1',30:'battery_android_2',40:'battery_android_3',50:'battery_android_3',60:'battery_android_4',70:'battery_android_5',80:'battery_android_5',90:'battery_android_6',100:'battery_android_full'}
for n,v in lv.items():
    M[f'battery-level-{n}-symbolic'] = '!' + v
    M[f'battery-level-{n}-charging-symbolic'] = '!battery_android_bolt'
M['battery-level-100-charged-symbolic'] = '!battery_android_bolt'
m('battery-missing', '!battery_android_question')
# "Classic" names provided by upower (used by the top bar)
m('battery-full', '!battery_android_full')
m('battery-good', '!battery_android_4')
m('battery-low', '!battery_android_2')
m('battery-caution', '!battery_android_1')
m('battery-empty', '!battery_android_0')
m('battery-full-charging battery-good-charging battery-low-charging battery-caution-charging battery-empty-charging battery-full-charged', '!battery_android_bolt')
# (no warning icon: Android shows the level, even when low)
# Quick settings
m('night-light', '!nightlight')
m('dark-mode', '!dark_mode')
m('airplane-mode', '!airplanemode_active')
m('notifications-disabled no-notifications', '!notifications_off')
m('power-profile-balanced', '!balance')
m('power-profile-performance', '!bolt')
m('power-profile-power-saver', '!eco')
m('input-keyboard', '!keyboard')
m('display-brightness', '!brightness_6')
m('keyboard-brightness-high keyboard-brightness-medium', '!backlight_high')
m('keyboard-brightness-off', '!backlight_low')
m('rotation-allowed', '!screen_rotation')
m('rotation-locked', '!screen_lock_rotation')
m('find-location location-services-active', '!location_on')
m('camera-web', '!videocam')
m('screen-shared', '!screen_share')
m('media-record record-screen', '!radio_button_checked')
m('screencast-stop', '!stop_circle')
m('screenshooter applets-screenshooter', '!screenshot_region')
m('system-shutdown', '!power_settings_new')
m('system-lock-screen', '!lock')
m('org.gnome.Settings emblem-system preferences-system', '!settings')
m('thunderbolt thunderbolt-acquiring', '!bolt')
m('accessibility-screen-reader', '!accessibility_new')
# Additions after on-screen checks
m('keyboard-brightness', '!backlight_high')
m('go-next pan-end', 'chevron_right')
m('go-previous pan-start', 'chevron_left')
# GSConnect (device icons loaded from the theme)
m('smartphone phone', '!smartphone')
m('tablet', '!tablet')
m('laptop', '!laptop_chromebook')
m('computer', '!computer')
m('tv', '!tv')
m('phonelink-ring', '!phonelink_ring')
# GSConnect indicator in the top bar
m('org.gnome.Shell.Extensions.GSConnect', '!smartphone')
# States seen in the top bar that were missing (they would fall back to Papirus)
m('bluetooth-disconnected', '!bluetooth')
m('bluetooth-hardware-disabled', '!bluetooth_disabled')
m('camera-disabled camera-hardware-disabled', '!videocam_off')
m('microphone-hardware-disabled', '!mic_off')
m('location-services-disabled', '!location_off')
m('airplane-mode-disabled', '!airplanemode_inactive')
m('night-light-disabled', '!bedtime_off')
m('network-wireless-hardware-disabled', '!signal_wifi_off')
m('network-cellular-hardware-disabled', '!signal_cellular_off')
m('network-cellular-no-route', '!signal_cellular_nodata')
m('network-no-route', '!signal_disconnected')
m('network-vpn-disconnected network-vpn-no-route', '!vpn_key_off')
m('network-idle network-transmit-receive', '!swap_vert')
m('network-transmit', '!arrow_upward')
m('network-receive', '!arrow_downward')
m('network-cellular-2g network-cellular-gprs', '!g_mobiledata')
m('network-cellular-edge', '!e_mobiledata')
m('network-cellular-3g', '!3g_mobiledata')
m('network-cellular-hspa', '!h_mobiledata')
m('network-cellular-4g', '!4g_mobiledata')
m('network-cellular-5g', '!5g')
for n,v in lv.items(): M[f'battery-level-{n}-plugged-in-symbolic'] = '!battery_android_bolt'
m('battery-action', '!battery_android_bolt')
