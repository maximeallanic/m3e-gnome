// Guards and helpers of the lock and login surfaces: logind check, GDM blocker, test user, bench lock / unlock.
//
// Layered guards. (1) logind: the nested Shell watches the REAL session (LoginManager.getCurrentSessionProxy,
// "Will monitor session ..." in shell.log) and ScreenShield._setLocked() writes LockedHint there. The link is cut
// from enable() by logind-guard.js (shared with the extensions bench: _setLocked replaced, Lock/Unlock handlers
// removed, _loginSession = null; the real session is kept in screenShield._bench.session). Here, before every
// nested lock, that cut is checked, and the real session's LockedHint is read again on closing (failure if it
// changed). No loginctl call, no logind Lock(): only Main.screenShield.lock() of the nested Shell.
// (2) GDM / PAM: the password prompt starts ShellUserVerifier.begin() -> Gdm.Client (real GDM daemon, PAM); begin
// is replaced by a local question ("Password:", secret) and the Gdm.Client methods that open a channel refuse and
// fail the scenario. gdm mode: GDM_GREETER_TEST=1 (nested.sh --mode gdm).
// (3) Real data: the displayed user is a test user (no real account name or picture); the real accounts of the
// login list are hidden for the scenario. No typing or click.
import Gdm from 'gi://Gdm';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as GdmUtil from 'resource:///org/gnome/shell/gdm/util.js';
import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';
import * as Signals from 'resource:///org/gnome/shell/misc/signals.js';

import {wait, waitUntil} from '../tools.js';
import {startLogindGuard} from '../logind-guard.js';

const GDM_METHODS = ['open_reauthentication_channel', 'open_reauthentication_channel_sync', 'get_user_verifier',
    'get_user_verifier_sync', 'get_greeter', 'get_greeter_sync', 'get_remote_greeter', 'get_remote_greeter_sync',
    'get_chooser', 'get_chooser_sync', 'get_manager', 'get_manager_sync'];

export const TEST_USER_NAME = 'bench';
export const TEST_USER_REAL_NAME = 'Test user';

// Test user (same interface as AccountsService.User for UserWidget, UserListItem, AuthPrompt).
export class TestUser extends Signals.EventEmitter {
    constructor(name, realName) {
        super();
        this._name = name;
        this._realName = realName;
        this.is_loaded = true;
        this.locked = false;
    }

    get_user_name() {
        return this._name;
    }

    get_real_name() {
        return this._realName;
    }

    is_logged_in() {
        return false;
    }

    get_icon_file() {
        return null;
    }

    is_system_account() {
        return false;
    }
}

export function blockGdm(ctx) {
    ctx.gdmRefused = [];
    ctx.gdmOriginals = {};
    const proto = Gdm.Client.prototype;
    for (const name of GDM_METHODS) {
        if (typeof proto[name] !== 'function')
            continue;
        ctx.gdmOriginals[name] = proto[name];
        proto[name] = function () {
            ctx.gdmRefused.push(name);
            throw new Error(`m3e-bench: Gdm.Client.${name} refused (the bench does not talk to the GDM daemon)`);
        };
    }
    const verifier = GdmUtil.ShellUserVerifier.prototype;
    ctx.gdmOriginals.begin = verifier.begin;
    // Local question, like the gdm-password service, after AuthPrompt.begin switched to VERIFYING.
    verifier.begin = function (userName, hold) {
        this._userName = userName;
        const id = GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
            this.emit('ask-question', 'gdm-password', 'Password:', true);
            hold?.release();
            return GLib.SOURCE_REMOVE;
        });
        GLib.Source.set_name_by_id(id, '[m3e-bench] test question');
    };
}

export function unblockGdm(ctx) {
    const originals = ctx.gdmOriginals ?? {};
    for (const name of GDM_METHODS) {
        if (originals[name])
            Gdm.Client.prototype[name] = originals[name];
    }
    if (originals.begin)
        GdmUtil.ShellUserVerifier.prototype.begin = originals.begin;
    ctx.gdmOriginals = null;
    if (ctx.gdmRefused?.length)
        throw new Error(`lock/login: call to the GDM daemon refused (${ctx.gdmRefused.join(', ')})`);
}

// Before every lock: the logind cut done by logind-guard.js at start-up must be done, and stay done.
async function checkLogindCut(ctx) {
    const shield = Main.screenShield;
    if (!shield)
        throw new Error('lock: no Main.screenShield');
    await startLogindGuard();
    if (!shield._bench)
        throw new Error('lock: logind session not resolved yet, lock refused');
    if (shield._loginSession !== null)
        throw new Error('lock: logind session set again, lock refused');
    const remaining = ['Lock', 'Unlock'].filter(n => shield._bench.session._signalConnectionsByName?.[n]?.length);
    if (remaining.length)
        throw new Error(`lock: signals ${remaining.join(', ')} of the real session still connected, lock refused`);
    ctx.lockedHintBefore = shield._bench.session.LockedHint;
    return shield;
}

function verifyLogind(ctx) {
    const shield = Main.screenShield;
    if (shield?._loginSession !== null)
        throw new Error('lock: logind session set again during the scenario');
    const after = shield._bench.session.LockedHint;
    if (after !== ctx.lockedHintBefore)
        throw new Error(`lock: LockedHint of the real session changed (${ctx.lockedHintBefore} -> ${after}): please check`);
}

// Lock of the nested Shell: lock() without animation, fade to black lifted as by user activity, blurred wallpaper
// hidden (plain background of #lockDialogGroup: measure.py finds the elements on a plain background). Displayed
// user = test user.
export async function lockBench(ctx) {
    const shield = await checkLogindCut(ctx);
    blockGdm(ctx);
    shield.lock(false);
    const dialog = await waitUntil(() => shield.locked && shield._lockScreenState === MessageTray.State.SHOWN &&
        shield._dialog, 5000);
    if (!dialog || !Main.sessionMode.isLocked)
        throw new Error('lock: lock screen not shown');
    shield._wakeUpScreen();
    await waitUntil(() => !shield._shortLightbox.visible && !shield._longLightbox.visible, 2000);
    dialog._backgroundGroup.hide();
    dialog._user = new TestUser(TEST_USER_NAME, TEST_USER_REAL_NAME);
    dialog._userName = TEST_USER_NAME;
    ctx.lockDialog = dialog;
    await wait(200);
    return dialog;
}

export async function unlockBench(ctx) {
    const shield = Main.screenShield;
    try {
        if (shield && (shield.locked || shield.active || shield._dialog)) {
            shield.deactivate(false);
            if (!await waitUntil(() => !shield._dialog && !shield.locked && !shield.active, 5000))
                throw new Error('lock: unlocking the nested Shell incomplete');
        }
        await waitUntil(() => !Main.sessionMode.isLocked, 2000);
        await wait(200);
    } finally {
        ctx.lockDialog = null;
        try {
            unblockGdm(ctx);
        } finally {
            if (shield?._bench)
                verifyLogind(ctx);
        }
    }
}
