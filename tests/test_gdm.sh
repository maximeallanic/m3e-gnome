#!/usr/bin/env bash
# GDM round trips inside a fake system root (see gdm_lib.sh): Debian (dpkg-divert), Ubuntu (update-alternatives), Arch and
# Fedora (in-place with a stock copy, package-manager hooks). Real dpkg-divert, update-alternatives, glib-compile-resources
# and dconf run against the fake root. Hook files for Fedora/Arch are checked for content only: the package managers
# themselves are not run (untested on real systems, see docs/gdm.md).
set -uo pipefail
# shellcheck source=tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
# shellcheck source=tests/gdm_lib.sh
source "$TESTS_DIR/gdm_lib.sh"

for tool in dpkg-divert update-alternatives glib-compile-resources gresource dconf; do
    if ! command -v "$tool" >/dev/null 2>&1; then echo "skipped: $tool not installed (apt install dpkg libglib2.0-dev-bin libglib2.0-bin dconf-cli)"; exit 0; fi
done

gdm_setup
trap t_teardown EXIT
gdm_make_data "$T_ROOT/data"
# same_except_stock DESCRIPTION BEFORE-SNAPSHOT-FILE : the current system equals BEFORE, ignoring the stock resource itself
# (a package update may have replaced it in between).
same_except_stock() {
    if diff <(grep -v 'gnome-shell-theme.gresource ' "$2") <(snap | grep -v 'gnome-shell-theme.gresource ') >/dev/null; then pass "$1"
    else fail "$1"; diff <(grep -v 'gnome-shell-theme.gresource ' "$2") <(snap | grep -v 'gnome-shell-theme.gresource ') | head -20; fi
}
SNAPSHOT_FILTER='diversions-old'   # dpkg-divert keeps the previous database next to the new one; dpkg's own behaviour

snap() { gdm_snapshot "$GR" | grep -v "$SNAPSHOT_FILTER"; }
gres() { gresource extract "$1" "/org/gnome/shell/theme/$2"; }
LIVE() { printf '%s' "$GR/usr/share/gnome-shell/gnome-shell-theme.gresource"; }

new_system() { # family
    GR="$T_ROOT/root-$1"
    gdm_make_root "$GR" "$1"
    snap >"$T_ROOT/before-$1.snap"
    gdm_install_helper_into "$GR"
}

common_checks() { # family  (after a successful apply)
    local f="$1" st="$GR/var/lib/m3e-gnome/gdm" u
    check "[$f] helper is root-owned code in libexec with a link in sbin" test -L "$GR/usr/local/sbin/m3e-gdm"
    check "[$f] manifest written" test -s "$st/manifest"
    check "[$f] staged data hash recorded" test -s "$st/data.sha256"
    check "[$f] dconf profile adds our database after user-db" bash -c "grep -n . '$GR/etc/dconf/profile/gdm' | sed -n '1,3p' | grep -q 'system-db:m3e-gdm'"
    check "[$f] dconf profile keeps the distribution's lines" grep -q 'greeter-dconf-defaults' "$GR/etc/dconf/profile/gdm"
    check "[$f] keyfile sets the cursor" grep -q "cursor-theme='Googlebook'" "$GR/etc/dconf/db/m3e-gdm.d/00-m3e-gdm"
    check "[$f] dconf database compiled" test -s "$GR/etc/dconf/db/m3e-gdm"
    check "[$f] icons installed system-wide" test -f "$GR/usr/local/share/icons/Material-Symbols/index.theme"
    check "[$f] cursor installed system-wide" test -f "$GR/usr/local/share/icons/Googlebook/cursors/left_ptr"
    check "[$f] font installed system-wide" test -f "$GR/usr/local/share/fonts/GoogleSansFlex/OFL.txt"
    check "[$f] blurred background installed" test -f "$GR/usr/local/share/m3e-gnome/gdm/background.png"
    for u in $(find "$GR/usr/local" "$GR/var/lib/m3e-gnome" -type f -perm /022 2>/dev/null | head -1); do fail "[$f] group/world-writable file: $u"; done
}

resource_checks() { # path-of-live-resource label
    local live="$1" f="$2" css
    for css in gnome-shell-light.css gnome-shell-dark.css; do
        check "[$f] $css carries the marker and the sheet" bash -c "gresource extract '$live' /org/gnome/shell/theme/$css | grep -qF 'm3e-gnome gdm'"
        check "[$f] $css keeps the stock sheet first" bash -c "gresource extract '$live' /org/gnome/shell/theme/$css | head -1 | grep -q 'stock'"
        check "[$f] $css has the background rule" bash -c "gresource extract '$live' /org/gnome/shell/theme/$css | grep -qF 'file:///usr/local/share/m3e-gnome/gdm/background.png'"
    done
    check "[$f] asset resource untouched" bash -c "gresource list '$live' | grep -q assets/toggle-on.svg"
}

echo "== Debian: dpkg-divert"
new_system debian
out="$(gdm_run apply --from "$T_ROOT/data" --dry-run 2>&1)"; rc=$?
check "dry run exits 0" test "$rc" -eq 0
check "dry run lists the divert" grep -q 'dpkg-divert' <<<"$out"
snap >"$T_ROOT/dry.snap"
if diff <(grep -v 'usr/local/\(libexec\|sbin\)' "$T_ROOT/dry.snap") <(grep -v 'usr/local/\(libexec\|sbin\)' "$T_ROOT/before-debian.snap") >/dev/null; then pass "dry run: the system is byte-identical"; else fail "dry run changed the system"; fi
if gdm_run apply --from "$T_ROOT/data" >"$T_ROOT/apply.out" 2>&1; then pass "apply exits 0"; else fail "apply failed"; cat "$T_ROOT/apply.out"; fi
common_checks debian
resource_checks "$(LIVE)" debian
check "[debian] the stock file is kept as .distrib" bash -c "gresource extract '$GR/usr/share/gnome-shell/gnome-shell-theme.gresource.distrib' /org/gnome/shell/theme/gnome-shell-dark.css | grep -q 'stock dark v1'"
check "[debian] dpkg-divert lists our diversion" bash -c "dpkg-divert --admindir '$GR/var/lib/dpkg' --instdir '$GR' --listpackage /usr/share/gnome-shell/gnome-shell-theme.gresource | grep -qx m3e-gnome"
check "[debian] apt hook installed" grep -q 'm3e-gdm refresh' "$GR/etc/apt/apt.conf.d/99m3e-gdm"
check "[debian] mechanism recorded" grep -qx divert "$GR/var/lib/m3e-gnome/gdm/mech"
snap >"$T_ROOT/applied-debian.snap"

echo "== Debian: verify (read-only section of verify.sh)"
if gdm_verify >"$T_ROOT/verify.out" 2>&1; then pass "verify passes after apply"; else fail "verify failed after apply"; cat "$T_ROOT/verify.out"; fi
cp "$GR/var/lib/m3e-gnome/gdm/data/theme.css" "$T_ROOT/theme.keep"; chmod u+w "$GR/var/lib/m3e-gnome/gdm/data/theme.css"
printf '.tampered{}\n' >>"$GR/var/lib/m3e-gnome/gdm/data/theme.css"
check_not "verify fails when the staged data was altered" gdm_verify
cp "$T_ROOT/theme.keep" "$GR/var/lib/m3e-gnome/gdm/data/theme.css"
cp "$GR/etc/apt/apt.conf.d/99m3e-gdm" "$T_ROOT/hook.keep"; rm "$GR/etc/apt/apt.conf.d/99m3e-gdm"
check_not "verify fails when the hook is gone" gdm_verify
cp "$T_ROOT/hook.keep" "$GR/etc/apt/apt.conf.d/99m3e-gdm"
chmod 666 "$GR/usr/local/libexec/m3e-gnome/gdm/cmd.sh"
check_not "verify fails when a helper file is writable by others" gdm_verify
chmod 644 "$GR/usr/local/libexec/m3e-gnome/gdm/cmd.sh"
cp "$GR/usr/share/gnome-shell/gnome-shell-theme.gresource.distrib" "$T_ROOT/distrib.keep"
gdm_make_stock "$GR/usr/share/gnome-shell/gnome-shell-theme.gresource.distrib" v9
check_not "verify fails when a package update changed the stock resource and no refresh ran" gdm_verify
cp "$T_ROOT/distrib.keep" "$GR/usr/share/gnome-shell/gnome-shell-theme.gresource.distrib"
check "verify passes again once restored" gdm_verify

echo "== Debian: idempotent re-apply and refresh"
gdm_ok apply --from "$T_ROOT/data"
check "the second apply reports success" grep -q 'installed' <<<"$GDM_OUT"
snap >"$T_ROOT/again.snap"
if cmp -s "$T_ROOT/applied-debian.snap" "$T_ROOT/again.snap"; then pass "re-apply leaves the system byte-identical"; else fail "re-apply changed something"; diff "$T_ROOT/applied-debian.snap" "$T_ROOT/again.snap" | head; fi
out="$(gdm_run refresh 2>&1)"
check "refresh with nothing to do is a no-op" grep -q 'up to date' <<<"$out"
snap >"$T_ROOT/refresh.snap"
check "…and changes nothing" cmp -s "$T_ROOT/applied-debian.snap" "$T_ROOT/refresh.snap"
# A package update writes the NEW stock resource to the diverted name.
gdm_make_stock "$GR/usr/share/gnome-shell/gnome-shell-theme.gresource.distrib" v2
gdm_ok refresh
check "after an update, refresh rebuilds from the new stock" bash -c "gresource extract '$(LIVE)' /org/gnome/shell/theme/gnome-shell-dark.css | grep -q 'stock dark v2'"
check "…and still carries the marker" bash -c "gresource extract '$(LIVE)' /org/gnome/shell/theme/gnome-shell-dark.css | grep -qF 'm3e-gnome gdm'"
check "…and the old stock text is gone" bash -c "! gresource extract '$(LIVE)' /org/gnome/shell/theme/gnome-shell-dark.css | grep -q 'stock dark v1'"

echo "== Debian: GNOME Shell major guard"
out="$(M3E_FAKE_GNOME_VERSION=48.1 gdm_run refresh 2>&1)"; rc=$?
check "refresh on another major exits 0" test "$rc" -eq 0
check "…and warns" grep -q 'not the verified version' <<<"$out"
check "…the stock sheet is back in service" bash -c "! gresource extract '$(LIVE)' /org/gnome/shell/theme/gnome-shell-dark.css | grep -qF 'm3e-gnome gdm'"
gdm_ok refresh
check "back on the tested major, refresh rebuilds" bash -c "gresource extract '$(LIVE)' /org/gnome/shell/theme/gnome-shell-dark.css | grep -qF 'm3e-gnome gdm'"
out="$(M3E_FAKE_GNOME_VERSION=48.1 gdm_run apply --from "$T_ROOT/data" --dry-run 2>&1)"; rc=$?
check "apply on another major is refused without --force" test "$rc" -ne 0
check "apply --force on another major goes on" env M3E_FAKE_GNOME_VERSION=48.1 bash -c "source '$TESTS_DIR/gdm_lib.sh'; GR='$GR'; gdm_run apply --from '$T_ROOT/data' --dry-run --force"

echo "== Debian: restore"
if gdm_run restore --remove-helper >"$T_ROOT/restore.out" 2>&1; then pass "restore exits 0"; else fail "restore failed"; cat "$T_ROOT/restore.out"; fi
snap >"$T_ROOT/after-debian.snap"
# The stock file is now the v2 one (a package update happened in between): compare everything else.
same_except_stock "restore: every other path is byte-identical to the pre-install state" "$T_ROOT/before-debian.snap"
check "restore: the NEW stock resource is back in place" bash -c "gresource extract '$(LIVE)' /org/gnome/shell/theme/gnome-shell-dark.css | grep -q 'stock dark v2'"
check "restore: no diversion left" bash -c "[ -z \"\$(dpkg-divert --admindir '$GR/var/lib/dpkg' --instdir '$GR' --list '*gnome-shell-theme*')\" ]"
# Without an update in between the whole tree is byte-identical.
gdm_install_helper_into "$GR"
gdm_ok apply --from "$T_ROOT/data"
gdm_ok restore --remove-helper
snap >"$T_ROOT/after2-debian.snap"
if cmp -s "$T_ROOT/after-debian.snap" "$T_ROOT/after2-debian.snap"; then pass "apply then restore again: byte-identical"; else fail "second round trip differs"; fi

echo "== Debian: refusals"
new_system debian
dpkg-divert --admindir "$GR/var/lib/dpkg" --instdir "$GR" --quiet --no-rename --add --package theme-gdm --divert /usr/share/gnome-shell/gnome-shell-theme.gresource.distrib /usr/share/gnome-shell/gnome-shell-theme.gresource
out="$(gdm_run apply --from "$T_ROOT/data" 2>&1)"; rc=$?
check "a diversion by another package (the old private script) is refused" test "$rc" -ne 0
check "…with the way out" grep -q 'theme-gdm --restore' <<<"$out"
new_system debian
rm -f "$GR/usr/lib/systemd/system/gdm.service"
out="$(gdm_run apply --from "$T_ROOT/data" 2>&1)"; rc=$?
check "no GDM installed: refused" test "$rc" -ne 0
check "…says why" grep -q 'GDM is not installed' <<<"$out"
printf 'ID=debian\n' >"$GR/etc/os-release"

echo "== Ubuntu: update-alternatives"
new_system ubuntu
UA=(update-alternatives --altdir "$GR/etc/alternatives" --admindir "$GR/var/lib/dpkg/alternatives")
before_alt="$("${UA[@]}" --query gdm-theme.gresource | sed "s|$GR||g")"
if gdm_run apply --from "$T_ROOT/data" >"$T_ROOT/ubuntu.out" 2>&1; then pass "apply exits 0"; else fail "apply failed"; cat "$T_ROOT/ubuntu.out"; fi
check "[ubuntu] mechanism is alternatives" grep -qx alternatives "$GR/var/lib/m3e-gnome/gdm/mech"
check "[ubuntu] our resource is the selected alternative" bash -c "'${UA[0]}' ${UA[*]:1} --query gdm-theme.gresource | grep -q '^Value: .*m3e-gnome/gdm/gdm-theme.gresource'"
resource_checks "$GR/usr/local/share/m3e-gnome/gdm/gdm-theme.gresource" ubuntu
check "[ubuntu] built on the highest-priority stock candidate (Yaru)" bash -c "gresource extract '$GR/usr/local/share/m3e-gnome/gdm/gdm-theme.gresource' /org/gnome/shell/theme/gnome-shell-dark.css | grep -q 'stock dark yaru'"
if diff <(grep '^f .*gnome-shell-theme.gresource' "$T_ROOT/before-ubuntu.snap") <(snap | grep '^f .*gnome-shell-theme.gresource') >/dev/null; then
    pass "[ubuntu] package-owned resources are untouched"; else fail "[ubuntu] a package-owned resource changed"; fi
common_checks ubuntu
check "[ubuntu] verify passes" gdm_verify
gdm_make_stock "$GR/usr/share/gnome-shell/theme/Yaru/gnome-shell-theme.gresource" yaru2
gdm_ok refresh
check "[ubuntu] refresh after an update uses the new Yaru resource" bash -c "gresource extract '$GR/usr/local/share/m3e-gnome/gdm/gdm-theme.gresource' /org/gnome/shell/theme/gnome-shell-dark.css | grep -q 'stock dark yaru2'"
gdm_ok restore --remove-helper
after_alt="$("${UA[@]}" --query gdm-theme.gresource | sed "s|$GR||g")"
check "[ubuntu] restore: the alternative is back to its previous state" test "$before_alt" = "$after_alt"
snap >"$T_ROOT/after-ubuntu.snap"
same_except_stock "[ubuntu] restore: byte-identical apart from the package-updated resource" "$T_ROOT/before-ubuntu.snap"

echo "== Arch / Fedora: in place, stock copy, hooks"
for fam in arch fedora; do
    new_system "$fam"
    orig="$(sha256sum "$(LIVE)" | cut -d' ' -f1)"
    if gdm_run apply --from "$T_ROOT/data" >"$T_ROOT/$fam.out" 2>&1; then pass "[$fam] apply exits 0"; else fail "[$fam] apply failed"; cat "$T_ROOT/$fam.out"; fi
    check "[$fam] mechanism is inplace" grep -qx inplace "$GR/var/lib/m3e-gnome/gdm/mech"
    resource_checks "$(LIVE)" "$fam"
    common_checks "$fam"
    M3E_OS_RELEASE="$GR/etc/os-release" check "[$fam] verify passes" gdm_verify
    check "[$fam] the stock bytes are kept" test "$(sha256sum "$GR/var/lib/m3e-gnome/gdm/stock/gnome-shell-theme.gresource" | cut -d' ' -f1)" = "$orig"
    gdm_make_stock "$(LIVE)" v3      # a package update overwrites the file
    gdm_ok refresh
    check "[$fam] refresh rebuilds from the updated stock" bash -c "gresource extract '$(LIVE)' /org/gnome/shell/theme/gnome-shell-dark.css | grep -q 'stock dark v3'"
    check "[$fam] …with our sheet" bash -c "gresource extract '$(LIVE)' /org/gnome/shell/theme/gnome-shell-dark.css | grep -qF 'm3e-gnome gdm'"
    gdm_ok restore --remove-helper
    check "[$fam] restore leaves the new stock resource" bash -c "gresource extract '$(LIVE)' /org/gnome/shell/theme/gnome-shell-dark.css | grep -q 'stock dark v3'"
    same_except_stock "[$fam] restore: everything else byte-identical" "$T_ROOT/before-$fam.snap"
done
new_system arch
arch_stock="$(sha256sum "$(LIVE)" | cut -d' ' -f1)"
gdm_ok apply --from "$T_ROOT/data"
check "[arch] pacman hook targets gnome-shell and runs refresh PostTransaction" bash -c "grep -q 'Target = gnome-shell' '$GR/etc/pacman.d/hooks/m3e-gdm.hook' && grep -q 'When = PostTransaction' '$GR/etc/pacman.d/hooks/m3e-gdm.hook' && grep -q 'Exec = /usr/local/sbin/m3e-gdm refresh' '$GR/etc/pacman.d/hooks/m3e-gdm.hook'"
gdm_ok restore --remove-helper
check "[arch] restore without an update puts the exact stock bytes back" test "$(sha256sum "$(LIVE)" | cut -d' ' -f1)" = "$arch_stock"
new_system fedora
gdm_ok apply --from "$T_ROOT/data"
check "[fedora] DNF 4 action file" grep -qx 'gnome-shell:in:/usr/local/sbin/m3e-gdm refresh --quiet' "$GR/etc/dnf/plugins/post-transaction-actions.d/m3e-gdm.action"
check "[fedora] DNF 5 actions file" grep -qx 'post_transaction:gnome-shell:in::/usr/local/sbin/m3e-gdm refresh --quiet' "$GR/etc/dnf/libdnf5-plugins/actions.d/m3e-gdm.actions"
gdm_ok restore --remove-helper

echo "== a pre-existing /etc/dconf/profile/gdm is kept and restored"
GR="$T_ROOT/root-profile"; gdm_make_root "$GR" debian
mkdir -p "$GR/etc/dconf/profile"; printf 'user-db:user\nsystem-db:gdm\nfile-db:/usr/share/gdm/greeter-dconf-defaults\n' >"$GR/etc/dconf/profile/gdm"
snap >"$T_ROOT/before-profile.snap"
gdm_install_helper_into "$GR"
gdm_ok apply --from "$T_ROOT/data"
check "profile gets our database and keeps system-db:gdm" bash -c "grep -q 'system-db:m3e-gdm' '$GR/etc/dconf/profile/gdm' && grep -q 'system-db:gdm' '$GR/etc/dconf/profile/gdm'"
gdm_ok restore --remove-helper
check "the original profile is back, byte for byte" bash -c "[ \"\$(cat '$GR/etc/dconf/profile/gdm')\" = \"\$(printf 'user-db:user\nsystem-db:gdm\nfile-db:/usr/share/gdm/greeter-dconf-defaults')\" ]"
same_except_stock "the rest is identical too" "$T_ROOT/before-profile.snap"

echo
if ((FAILS)); then echo "gdm round trip: $FAILS failure(s)"; exit 1; fi
echo "gdm round trip: all checks passed"
