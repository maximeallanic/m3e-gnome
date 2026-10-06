#!/usr/bin/env bash
# Install -> verify -> reinstall -> uninstall round trip inside a throw-away HOME (see lib.sh). The pinned sources are
# replaced by local git fixtures; only npm (material-color-utilities) and, when no matugen is on PATH, the pinned
# matugen release are downloaded. M3E_TEST_OFFLINE=1 stubs npm (needs tools/material-palette/node_modules).
set -uo pipefail
# shellcheck source=tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
# shellcheck source=tests/fixtures.sh
source "$TESTS_DIR/fixtures.sh"

t_setup
trap t_teardown EXIT
make_fixtures
if [[ -n "${M3E_TEST_OFFLINE:-}" ]]; then
    real_npm="$(PATH="$ORIG_PATH" command -v npm)"
    rm -f "$T_ROOT/realbin/npm"
    # shellcheck disable=SC2016  # literal $ for the generated stub
    printf '#!/bin/sh\n[ "$1" = ci ] && [ -x "%s/tools/material-palette/node_modules/.bin/esbuild" ] && exit 0\nexec %s "$@"\n' \
        "$REPO" "$real_npm" >"$T_ROOT/realbin/npm"
    chmod +x "$T_ROOT/realbin/npm"
fi

echo "== pre-install state: user files that the installer must back up and restore"
mkdir -p "$HOME/.config/gtk-4.0" "$HOME/.config/matugen" "$HOME/.icons/default" "$HOME/.local/share/icons/Papirus-Dark" "$HOME/.local/bin"
printf '/* my own css */\n' >"$HOME/.config/gtk-4.0/gtk.css"
chmod 600 "$HOME/.config/gtk-4.0/gtk.css"
printf '[config]\n# my matugen config\n' >"$HOME/.config/matugen/config.toml"
printf '[Icon Theme]\nInherits=Adwaita\n' >"$HOME/.icons/default/index.theme"
printf 'mine\n' >"$HOME/.local/share/icons/Papirus-Dark/my-file"
printf '#!/bin/sh\necho mine\n' >"$HOME/.local/bin/unrelated"; chmod 755 "$HOME/.local/bin/unrelated"
make_wallpaper "$HOME/wallpaper.png"
fake_set /org/gnome/desktop/interface/gtk-theme "'Adwaita'"
fake_set /org/gnome/desktop/interface/color-scheme "'prefer-light'"
fake_set /org/gnome/shell/enabled-extensions "['foo@example.invalid']"
fake_set /org/gnome/desktop/background/picture-uri-dark "'file://$HOME/wallpaper.png'"
fake_set /org/gnome/desktop/background/picture-uri "'file://$HOME/wallpaper.png'"
snapshot "$HOME" >"$T_ROOT/before.snap"
cp "$M3E_FAKE_DIR/dconf.json" "$T_ROOT/dconf.before"

# The cursor build downloads the AOSP vector drawables: only with M3E_TEST_NETWORK=1.
SKIP=(--skip cursor)
[[ -z "${M3E_TEST_NETWORK:-}" ]] || SKIP=()
INSTALL=(bash "$REPO/install.sh" "${SKIP[@]}")
echo "== dry run changes nothing"
"${INSTALL[@]}" --dry-run >"$T_ROOT/dry.out" 2>&1 || { cat "$T_ROOT/dry.out"; fail "dry run exited non-zero"; }
snapshot "$HOME" >"$T_ROOT/dry.snap"
check "dry run leaves HOME untouched" cmp -s "$T_ROOT/before.snap" "$T_ROOT/dry.snap"
check "dry run leaves the fake settings untouched" cmp -s "$T_ROOT/dconf.before" "$M3E_FAKE_DIR/dconf.json"
check "dry run lists actions" grep -q 'dry-run' "$T_ROOT/dry.out"

echo "== install"
if "${INSTALL[@]}" >"$T_ROOT/install.out" 2>&1; then pass "install exits 0"; else fail "install failed"; cat "$T_ROOT/install.out"; fi
check "manifest written" test -s "$HOME/.local/share/m3e-gnome/manifest"
# shellcheck disable=SC2016  # $1 expands inside the child shell
check "pre-existing gtk.css was backed up" bash -c 'grep -q "my own css" "$1"/.local/share/m3e-gnome/backup/*/files/"${1#/}"/.config/gtk-4.0/gtk.css' _ "$HOME"
check "gtk.css now imports the theme" grep -q 'm3e-gtk4.css' "$HOME/.config/gtk-4.0/gtk.css"
check "the user's own matugen config is left alone" grep -qx '# my matugen config' "$HOME/.config/matugen/config.toml"
check "the theme's matugen config is in its own directory" test -s "$HOME/.config/m3e-gnome/matugen/config.toml"
check "post_hook commands ran with a HOME containing a space" test -s "$HOME/.themes/M3E-Shell/gnome-shell/gnome-shell.css"
check "user script untouched" grep -q mine "$HOME/.local/bin/unrelated"
check "gtk-theme set" test "$(fake_get /org/gnome/desktop/interface/gtk-theme)" = "'Material-Gnome'"
check "service active" systemctl --user is-active -q material-sync.service
check "extension enabled list keeps the user's entry" grep -q 'foo@example.invalid' "$M3E_FAKE_DIR/dconf.json"

echo "== verify"
if bash "$REPO/verify.sh" "${SKIP[@]}" >"$T_ROOT/verify.out" 2>&1; then pass "verify passes after install"; else fail "verify failed"; grep -v '^OK' "$T_ROOT/verify.out"; fi

echo "== idempotent reinstall"
cp "$HOME/.local/share/m3e-gnome/manifest" "$T_ROOT/manifest.1"
if "${INSTALL[@]}" >"$T_ROOT/install2.out" 2>&1; then pass "second install exits 0"; else fail "second install failed"; cat "$T_ROOT/install2.out"; fi
check "manifest has no duplicate entries" bash -c "[ \"\$(sort '$HOME/.local/share/m3e-gnome/manifest' | uniq -d | wc -l)\" = 0 ]"
check "second install did not back up its own files again" bash -c "[ \"\$(ls '$HOME/.local/share/m3e-gnome/backup' | wc -l)\" = 1 ]"
check "verify passes after reinstall" bash "$REPO/verify.sh" "${SKIP[@]}"

echo "== GDM (opt-in): user-side data preparation, then the whole flow against a fake system root"
# shellcheck source=tests/gdm_lib.sh
source "$TESTS_DIR/gdm_lib.sh"
if have_all() { for t in "$@"; do command -v "$t" >/dev/null 2>&1 || return 1; done; }; have_all dpkg-divert glib-compile-resources gresource /usr/bin/dconf; then
    GR="$T_ROOT/gdm-root"
    # shellcheck disable=SC2031
    export M3E_GDM_ROOT="$GR"
    gdm_make_root "$GR" debian
    snapshot "$GR" | grep -v diversions-old >"$T_ROOT/gdm-before.snap"
    GDM_ENV=(env)
    "${GDM_ENV[@]}" bash "$REPO/install.sh" --gdm-only --dry-run --yes --no-session-check >"$T_ROOT/gdm-dry.out" 2>&1 || { fail "gdm dry run failed"; cat "$T_ROOT/gdm-dry.out"; }
    snapshot "$GR" | grep -v diversions-old >"$T_ROOT/gdm-dry.snap"
    check "gdm dry run changes nothing in the system root" cmp -s "$T_ROOT/gdm-before.snap" "$T_ROOT/gdm-dry.snap"
    check "gdm dry run shows the plan" grep -q 'dry-run' "$T_ROOT/gdm-dry.out"
    if "${GDM_ENV[@]}" bash "$REPO/install.sh" --gdm-only --yes --no-session-check >"$T_ROOT/gdm-install.out" 2>&1; then pass "install.sh --gdm-only exits 0"
    else fail "install.sh --gdm-only failed"; tail -20 "$T_ROOT/gdm-install.out"; fi
    check "the rendered stylesheet landed in the staged data" grep -q 'lockDialogGroup' "$GR/var/lib/m3e-gnome/gdm/data/theme.css"
    check "the blurred wallpaper was staged as a PNG" bash -c "head -c 8 '$GR/var/lib/m3e-gnome/gdm/data/background.png' | grep -q PNG"
    check "the staged stylesheet was stripped of comments user-side" bash -c "! grep -q '/\\*' '$GR/var/lib/m3e-gnome/gdm/data/theme.css'"
    check "the staged stylesheet has no template placeholder" bash -c "! grep -q '{{' '$GR/var/lib/m3e-gnome/gdm/data/theme.css'"
    check "the live resource carries the M3E sheet" bash -c "gresource extract '$GR/usr/share/gnome-shell/gnome-shell-theme.gresource' /org/gnome/shell/theme/gnome-shell-dark.css | grep -qF 'm3e-gnome gdm'"
    check "verify.sh includes the GDM section and passes" "${GDM_ENV[@]}" bash "$REPO/verify.sh" "${SKIP[@]}"
    check "the user-side step did not touch HOME beyond temp files" bash -c "[ -z \"\$(find '$TMPDIR' -maxdepth 1 -name 'm3e-gnome.*')\" ]"
    check "uninstall.sh --gdm --dry-run changes nothing" bash -c "$(printf '%q ' "${GDM_ENV[@]}") bash '$REPO/uninstall.sh' --gdm --dry-run --yes >/dev/null && test -f '$GR/var/lib/m3e-gnome/gdm/manifest'"
    if "${GDM_ENV[@]}" bash "$REPO/uninstall.sh" --gdm --yes >"$T_ROOT/gdm-uninstall.out" 2>&1; then pass "uninstall.sh --gdm exits 0"; else fail "uninstall.sh --gdm failed"; cat "$T_ROOT/gdm-uninstall.out"; fi
    snapshot "$GR" | grep -v diversions-old >"$T_ROOT/gdm-after.snap"
    if cmp -s "$T_ROOT/gdm-before.snap" "$T_ROOT/gdm-after.snap"; then pass "the system root is byte-identical after uninstall --gdm"
    else fail "system root differs after uninstall --gdm"; diff "$T_ROOT/gdm-before.snap" "$T_ROOT/gdm-after.snap" | head -20; fi
    # The full uninstall below must revert the GDM theming too.
    bash "$REPO/install.sh" --gdm-only --yes --no-session-check >/dev/null 2>&1 || fail "second gdm install failed"
    GDM_REINSTALLED=1
else
    echo "  skipped: needs dpkg-divert, glib-compile-resources, gresource and the real dconf"
fi

echo "== uninstall"
check "uninstall --dry-run changes nothing" bash -c "bash '$REPO/uninstall.sh' --dry-run --yes >/dev/null && test -f '$HOME/.local/share/m3e-gnome/manifest'"
if bash "$REPO/uninstall.sh" --yes >"$T_ROOT/uninstall.out" 2>&1; then pass "uninstall exits 0"; else fail "uninstall failed"; cat "$T_ROOT/uninstall.out"; fi
if [[ -n "${GDM_REINSTALLED:-}" ]]; then
    snapshot "$GR" | grep -v diversions-old >"$T_ROOT/gdm-after-full.snap"
    check "the full uninstall also reverted the GDM theming (system root byte-identical)" cmp -s "$T_ROOT/gdm-before.snap" "$T_ROOT/gdm-after-full.snap"
fi
snapshot "$HOME" >"$T_ROOT/after.snap"
if cmp -s "$T_ROOT/before.snap" "$T_ROOT/after.snap"; then pass "HOME is identical to its pre-install state"
else fail "HOME differs after uninstall"; diff "$T_ROOT/before.snap" "$T_ROOT/after.snap" | head -40; fi
if python3 - "$T_ROOT/dconf.before" "$M3E_FAKE_DIR/dconf.json" <<'PY'
import json, sys
a, b = (json.load(open(f)) for f in sys.argv[1:3])
bad = {k: (a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)}
if bad:
    print(bad)
sys.exit(1 if bad else 0)
PY
then pass "settings are back to their pre-install values"; else fail "settings differ after uninstall"; fi
check "service stopped" bash -c "! systemctl --user is-active -q material-sync.service"
check_not "no leftover m3e-gnome temp directories" bash -c "find '$TMPDIR' -maxdepth 1 -name 'm3e-gnome.*' | grep -q ."

if [[ -n "${M3E_TEST_EXTENSIONS_REPO:-}" ]]; then
    echo "== install with the real companion extensions repository"
    if bash "$REPO/install.sh" "${SKIP[@]}" --extensions-dir "$M3E_TEST_EXTENSIONS_REPO" >"$T_ROOT/real-ext.out" 2>&1 &&
        bash "$REPO/verify.sh" "${SKIP[@]}" >"$T_ROOT/real-ext-verify.out" 2>&1; then pass "real extensions install and verify"
    else fail "real extensions round trip"; tail -20 "$T_ROOT/real-ext.out" "$T_ROOT/real-ext-verify.out"; fi
    bash "$REPO/uninstall.sh" --yes >/dev/null 2>&1
    snapshot "$HOME" >"$T_ROOT/after2.snap"
    check "HOME identical again after uninstalling the real-extensions install" cmp -s "$T_ROOT/before.snap" "$T_ROOT/after2.snap"
fi

echo
if ((FAILS)); then echo "round trip: $FAILS failure(s)"; exit 1; fi
echo "round trip: all checks passed"
