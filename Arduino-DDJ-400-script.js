// Arduino-DDJ-400-script.js
// ****************************************************************************
// * Mixxx mapping script file for the Pioneer DDJ-400.
// * Authors: Warker, nschloe, dj3730, jusko, tiesjan
// * Reviewers: Be-ing, Holzhaus
// * Manual: https://manual.mixxx.org/2.3/en/hardware/controllers/pioneer_ddj_400.html
// ****************************************************************************
//
//  Implemented (as per manufacturer's manual):
//      * Mixer Section (Faders, EQ, Filter, Gain, Cue)
//      * Browsing and loading + Waveform zoom (shift)
//      * Jogwheels, Scratching, Bending, Loop adjust
//      * Cycle Temporange
//      * Beat Sync
//      * Hot Cue Mode
//      * Beat Loop Mode
//      * Beat Jump Mode
//      * Sampler Mode
//
//  Custom (Mixxx specific mappings):
//      * BeatFX: Assigned Effect Unit 1
//                < LEFT toggles focus between Effects 1, 2 and 3 leftward
//                > RIGHT toggles focus between Effects 1, 2 and 3 rightward
//                v DOWN loads next effect entry for focused Effect
//                SHIFT + v UP loads previous effect entry for focused Effect
//                LEVEL/DEPTH controls the Mix knob of the Effect Unit
//                SHIFT + LEVEL/DEPTH controls the Meta knob of the focused Effect
//                ON/OFF toggles focused effect slot
//                SHIFT + ON/OFF disables all three effect slots.
//      * 32 beat jump forward & back (Shift + </> CUE/LOOP CALL arrows)
//      * Toggle quantize (Shift + channel cue)
//
//  Not implemented (after discussion and trial attempts):
//      * Loop Section:
//        * -4BEAT auto loop (hacky---prefer a clean way to set a 4 beat loop
//                            from a previous position on long press)
//        * CUE/LOOP CALL - memory & delete (complex and not useful. Hot cues are sufficient)
//
//      * Secondary pad modes (trial attempts complex and too experimental)
//        * Keyboard mode
//        * Pad FX1
//        * Pad FX2
//        * Keyshift mode

var ArduinoDDJ400 = {};

ArduinoDDJ400.lights = {
    beatFx: {
        status: 0x94,
        data1: 0x47,
    },
    shiftBeatFx: {
        status: 0x94,
        data1: 0x43,
    },
    deck1: {
        vuMeter: {
            status: 0xB0,
            data1: 0x02,
        },
        playPause: {
            status: 0x90,
            data1: 0x0B,
        },
        shiftPlayPause: {
            status: 0x90,
            data1: 0x47,
        },
        cue: {
            status: 0x90,
            data1: 0x0C,
        },
        shiftCue: {
            status: 0x90,
            data1: 0x48,
        },
    },
    deck2: {
        vuMeter: {
            status: 0xB0,
            data1: 0x02,
        },
        playPause: {
            status: 0x91,
            data1: 0x0B,
        },
        shiftPlayPause: {
            status: 0x91,
            data1: 0x47,
        },
        cue: {
            status: 0x91,
            data1: 0x0C,
        },
        shiftCue: {
            status: 0x91,
            data1: 0x48,
        },
    },
};

// Store timer IDs
ArduinoDDJ400.timers = {};

// Jog wheel constants
ArduinoDDJ400.vinylMode = true;
ArduinoDDJ400.alpha = 1.0/8;
ArduinoDDJ400.beta = ArduinoDDJ400.alpha/32;

// Multiplier for fast seek through track using SHIFT+JOGWHEEL
ArduinoDDJ400.fastSeekScale = 150;
ArduinoDDJ400.bendScale = 0.8;

ArduinoDDJ400.tempoRanges = [0.06, 0.10, 0.16, 0.25];

ArduinoDDJ400.shiftButtonDown = [false, false];

// Jog wheel loop adjust
ArduinoDDJ400.loopAdjustIn = [false, false];
ArduinoDDJ400.loopAdjustOut = [false, false];
ArduinoDDJ400.loopAdjustMultiply = 50;

// Beatjump pad (beatjump_size values)
ArduinoDDJ400.beatjumpSizeForPad = {
    0x20: -1, // PAD 1
    0x21: 1,  // PAD 2
    0x22: -2, // PAD 3
    0x23: 2,  // PAD 4
    0x24: -4, // PAD 5
    0x25: 4,  // PAD 6
    0x26: -8, // PAD 7
    0x27: 8   // PAD 8
};

ArduinoDDJ400.quickJumpSize = 32;

// Used for tempo slider
ArduinoDDJ400.highResMSB = {
    "[Channel1]": {},
    "[Channel2]": {}
};

ArduinoDDJ400.trackLoadedLED = function(value, group, _control) {
    midi.sendShortMsg(
        0x9F,
        group.match(script.channelRegEx)[1] - 1,
        value > 0 ? 0x7F : 0x00
    );
};

ArduinoDDJ400.toggleLight = function(midiIn, active) {
    midi.sendShortMsg(midiIn.status, midiIn.data1, active ? 0x7F : 0);
};

ArduinoDDJ400.displaySysexManufacturerId = 0x7D;
ArduinoDDJ400.displayTimer = 0;
ArduinoDDJ400.displayDeckGroups = ["[Channel1]", "[Channel2]"];
ArduinoDDJ400.hasPlayerApi = typeof engine.getPlayer === "function";
ArduinoDDJ400.displayBpmPlaceholder = "-.-";
ArduinoDDJ400.displayKeyPlaceholder = "--";
ArduinoDDJ400.camelotKeys = {
    1: "8B",
    2: "3B",
    3: "10B",
    4: "5B",
    5: "12B",
    6: "7B",
    7: "2B",
    8: "9B",
    9: "4B",
    10: "11B",
    11: "6B",
    12: "1B",
    13: "5A",
    14: "12A",
    15: "7A",
    16: "2A",
    17: "9A",
    18: "4A",
    19: "11A",
    20: "6A",
    21: "1A",
    22: "8A",
    23: "3A",
    24: "10A"
};
ArduinoDDJ400.classicalKeys = {
    1: "C",
    2: "Db",
    3: "D",
    4: "Eb",
    5: "E",
    6: "F",
    7: "F#/Gb",
    8: "G",
    9: "Ab",
    10: "A",
    11: "Bb",
    12: "B",
    13: "Cm",
    14: "C#m",
    15: "Dm",
    16: "D#m/Ebm",
    17: "Em",
    18: "Fm",
    19: "F#m",
    20: "Gm",
    21: "G#m",
    22: "Am",
    23: "Bbm",
    24: "Bm"
};

ArduinoDDJ400.sendDisplayLine = function(line) {
    const message = [0xF0, ArduinoDDJ400.displaySysexManufacturerId];

    for (let i = 0; i < line.length; ++i) {
        message.push(line.charCodeAt(i) & 0x7F);
    }

    message.push(0xF7);
    midi.sendSysexMsg(message, message.length);
};

ArduinoDDJ400.formatDisplayText = function(value) {
    return String(value || "")
        .replace(/[\r\n]+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
};

ArduinoDDJ400.sendDisplayField = function(name, value) {
    ArduinoDDJ400.sendDisplayLine(name + ":" + ArduinoDDJ400.formatDisplayText(value));
};

ArduinoDDJ400.formatDisplayKey = function(value) {
    if (value === undefined || value === null || value === "") {
        return ArduinoDDJ400.displayKeyPlaceholder;
    }

    const numericKey = Number(value);
    if (Number.isInteger(numericKey) && ArduinoDDJ400.camelotKeys[numericKey]) {
        const camelotKey = ArduinoDDJ400.camelotKeys[numericKey];
        const classicalKey = ArduinoDDJ400.classicalKeys[numericKey];
        return classicalKey ? camelotKey + "(" + classicalKey + ")" : camelotKey;
    }

    const keyText = String(value).trim();
    return keyText || ArduinoDDJ400.displayKeyPlaceholder;
};

ArduinoDDJ400.getDeckDisplaySnapshot = function(group) {
    const player = ArduinoDDJ400.hasPlayerApi ? engine.getPlayer(group) : null;
    const bpm = engine.getValue(group, "bpm");
    const duration = engine.getValue(group, "duration");
    const playposition = engine.getValue(group, "playposition");
    const elapsed = duration > 0 ? Math.max(0, Math.round(duration * Math.max(0, playposition))) : 0;
    const legacyKey = engine.getValue(group, "key");

    return {
        bpm: bpm > 0 ? bpm.toFixed(1) : ArduinoDDJ400.displayBpmPlaceholder,
        key: ArduinoDDJ400.formatDisplayKey(player ? player.key : legacyKey),
        title: player ? player.title : "",
        artist: player ? player.artist : "",
        play: engine.getValue(group, "play") ? "1" : "0",
        loaded: engine.getValue(group, "track_loaded") ? "1" : "0",
        loop: engine.getValue(group, "loop_enabled") ? "1" : "0",
        elapsed: String(elapsed),
        duration: String(duration > 0 ? Math.round(duration) : 0),
    };
};

ArduinoDDJ400.sendDeckDisplayState = function(_value, group, _control) {
    const deck = group === "[Channel1]" ? "D1" : "D2";
    const snapshot = ArduinoDDJ400.getDeckDisplaySnapshot(group);

    ArduinoDDJ400.sendDisplayField(deck + "_BPM", snapshot.bpm);
    ArduinoDDJ400.sendDisplayField(deck + "_KEY", snapshot.key);
    ArduinoDDJ400.sendDisplayField(deck + "_TITLE", snapshot.title);
    ArduinoDDJ400.sendDisplayField(deck + "_ARTIST", snapshot.artist);
    ArduinoDDJ400.sendDisplayField(deck + "_PLAY", snapshot.play);
    ArduinoDDJ400.sendDisplayField(deck + "_LOADED", snapshot.loaded);
    ArduinoDDJ400.sendDisplayField(deck + "_LOOP", snapshot.loop);
    ArduinoDDJ400.sendDisplayField(deck + "_ELAPSED", snapshot.elapsed);
    ArduinoDDJ400.sendDisplayField(deck + "_DURATION", snapshot.duration);
};

ArduinoDDJ400.sendRecordingDisplayState = function(value, _group, _control) {
    ArduinoDDJ400.sendDisplayField("REC_STATUS", value > 0 ? "1" : "0");
};

ArduinoDDJ400.sendDisplayHeartbeat = function() {
    ArduinoDDJ400.displayDeckGroups.forEach(function(group) {
        ArduinoDDJ400.sendDeckDisplayState(0, group, "");
    });
    ArduinoDDJ400.sendRecordingDisplayState(engine.getValue("[Recording]", "status"), "[Recording]", "status");
};

//
// Init
//

ArduinoDDJ400.init = function() {
    engine.setValue("[EffectRack1_EffectUnit1]", "show_focus", 1);

    engine.makeUnbufferedConnection("[Channel1]", "vu_meter", ArduinoDDJ400.vuMeterUpdate);
    engine.makeUnbufferedConnection("[Channel2]", "vu_meter", ArduinoDDJ400.vuMeterUpdate);

    ArduinoDDJ400.toggleLight(ArduinoDDJ400.lights.deck1.vuMeter, false);
    ArduinoDDJ400.toggleLight(ArduinoDDJ400.lights.deck2.vuMeter, false);

    engine.softTakeover("[Channel1]", "rate", true);
    engine.softTakeover("[Channel2]", "rate", true);
    engine.softTakeover("[EffectRack1_EffectUnit1_Effect1]", "meta", true);
    engine.softTakeover("[EffectRack1_EffectUnit1_Effect2]", "meta", true);
    engine.softTakeover("[EffectRack1_EffectUnit1_Effect3]", "meta", true);
    engine.softTakeover("[EffectRack1_EffectUnit1]", "mix", true);

    const samplerCount = 16;
    if (engine.getValue("[App]", "num_samplers") < samplerCount) {
        engine.setValue("[App]", "num_samplers", samplerCount);
    }
    for (let i = 1; i <= samplerCount; ++i) {
        engine.makeConnection("[Sampler" + i + "]", "play", ArduinoDDJ400.samplerPlayOutputCallbackFunction);
    }

    engine.makeConnection("[Channel1]", "track_loaded", ArduinoDDJ400.trackLoadedLED);
    engine.makeConnection("[Channel2]", "track_loaded", ArduinoDDJ400.trackLoadedLED);
    engine.makeConnection("[Channel1]", "bpm", ArduinoDDJ400.sendDeckDisplayState);
    engine.makeConnection("[Channel2]", "bpm", ArduinoDDJ400.sendDeckDisplayState);
    engine.makeConnection("[Channel1]", "play", ArduinoDDJ400.sendDeckDisplayState);
    engine.makeConnection("[Channel2]", "play", ArduinoDDJ400.sendDeckDisplayState);
    engine.makeConnection("[Channel1]", "track_loaded", ArduinoDDJ400.sendDeckDisplayState);
    engine.makeConnection("[Channel2]", "track_loaded", ArduinoDDJ400.sendDeckDisplayState);
    engine.makeConnection("[Channel1]", "loop_enabled", ArduinoDDJ400.sendDeckDisplayState);
    engine.makeConnection("[Channel2]", "loop_enabled", ArduinoDDJ400.sendDeckDisplayState);
    engine.makeConnection("[Recording]", "status", ArduinoDDJ400.sendRecordingDisplayState);

    // play the "track loaded" animation on both decks at startup
    midi.sendShortMsg(0x9F, 0x00, 0x7F);
    midi.sendShortMsg(0x9F, 0x01, 0x7F);

    ArduinoDDJ400.setLoopButtonLights(0x90, 0x7F);
    ArduinoDDJ400.setLoopButtonLights(0x91, 0x7F);

    engine.makeConnection("[Channel1]", "loop_enabled", ArduinoDDJ400.loopToggle);
    engine.makeConnection("[Channel2]", "loop_enabled", ArduinoDDJ400.loopToggle);

    for (let i = 1; i <= 3; i++) {
        engine.makeConnection("[EffectRack1_EffectUnit1_Effect" + i +"]", "enabled", ArduinoDDJ400.toggleFxLight);
    }
    engine.makeConnection("[EffectRack1_EffectUnit1]", "focused_effect", ArduinoDDJ400.toggleFxLight);

    ArduinoDDJ400.displayTimer = engine.beginTimer(1000, ArduinoDDJ400.sendDisplayHeartbeat);
    ArduinoDDJ400.sendDisplayHeartbeat();

    // query the controller for current control positions on startup
    midi.sendSysexMsg([0xF0, 0x00, 0x40, 0x05, 0x00, 0x00, 0x02, 0x06, 0x00, 0x03, 0x01, 0xf7], 12);
};

//
// Channel level lights
//

ArduinoDDJ400.vuMeterUpdate = function(value, group) {
    const newVal = value * 150;

    switch (group) {
    case "[Channel1]":
        midi.sendShortMsg(0xB0, 0x02, newVal);
        break;

    case "[Channel2]":
        midi.sendShortMsg(0xB1, 0x02, newVal);
        break;
    }
};

//
// Effects
//

ArduinoDDJ400.toggleFxLight = function(_value, _group, _control) {
    const enabled = engine.getValue(ArduinoDDJ400.focusedFxGroup(), "enabled");

    ArduinoDDJ400.toggleLight(ArduinoDDJ400.lights.beatFx, enabled);
    ArduinoDDJ400.toggleLight(ArduinoDDJ400.lights.shiftBeatFx, enabled);
};

ArduinoDDJ400.focusedFxGroup = function() {
    const focusedFx = engine.getValue("[EffectRack1_EffectUnit1]", "focused_effect");
    return "[EffectRack1_EffectUnit1_Effect" + focusedFx + "]";
};

ArduinoDDJ400.beatFxLevelDepthRotate = function(_channel, _control, value) {
    if (ArduinoDDJ400.shiftButtonDown[0] || ArduinoDDJ400.shiftButtonDown[1]) {
        engine.softTakeoverIgnoreNextValue("[EffectRack1_EffectUnit1]", "mix");
        engine.setParameter(ArduinoDDJ400.focusedFxGroup(), "meta", value / 0x7F);
    } else {
        engine.softTakeoverIgnoreNextValue(ArduinoDDJ400.focusedFxGroup(), "meta");
        engine.setParameter("[EffectRack1_EffectUnit1]", "mix", value / 0x7F);
    }
};

ArduinoDDJ400.changeFocusedEffectBy = function(numberOfSteps) {
    let focusedEffect = engine.getValue("[EffectRack1_EffectUnit1]", "focused_effect");

    // Convert to zero-based index
    focusedEffect -= 1;

    // Standard Euclidean modulo by use of two plain modulos
    const numberOfEffectsPerEffectUnit = 3;
    focusedEffect = (((focusedEffect + numberOfSteps) % numberOfEffectsPerEffectUnit) + numberOfEffectsPerEffectUnit) % numberOfEffectsPerEffectUnit;

    // Convert back to one-based index
    focusedEffect += 1;

    engine.setValue("[EffectRack1_EffectUnit1]", "focused_effect", focusedEffect);
};

ArduinoDDJ400.beatFxLeftPressed = function(_channel, _control, value) {
    if (value === 0) { return; }

    ArduinoDDJ400.changeFocusedEffectBy(-1);
};

ArduinoDDJ400.beatFxRightPressed = function(_channel, _control, value) {
    if (value === 0) { return; }

    ArduinoDDJ400.changeFocusedEffectBy(1);
};

ArduinoDDJ400.beatFxSelectPressed = function(_channel, _control, value) {
    if (value === 0) { return; }

    engine.setValue(ArduinoDDJ400.focusedFxGroup(), "next_effect", value);
};

ArduinoDDJ400.beatFxSelectShiftPressed = function(_channel, _control, value) {
    if (value === 0) { return; }

    engine.setValue(ArduinoDDJ400.focusedFxGroup(), "prev_effect", value);
};

ArduinoDDJ400.beatFxOnOffPressed = function(_channel, _control, value) {
    if (value === 0) { return; }

    const toggleEnabled = !engine.getValue(ArduinoDDJ400.focusedFxGroup(), "enabled");
    engine.setValue(ArduinoDDJ400.focusedFxGroup(), "enabled", toggleEnabled);
};

ArduinoDDJ400.beatFxOnOffShiftPressed = function(_channel, _control, value) {
    if (value === 0) { return; }

    engine.setParameter("[EffectRack1_EffectUnit1]", "mix", 0);
    engine.softTakeoverIgnoreNextValue("[EffectRack1_EffectUnit1]", "mix");

    for (let i = 1; i <= 3; i++) {
        engine.setValue("[EffectRack1_EffectUnit1_Effect" + i + "]", "enabled", 0);
    }
    ArduinoDDJ400.toggleLight(ArduinoDDJ400.lights.beatFx, false);
    ArduinoDDJ400.toggleLight(ArduinoDDJ400.lights.shiftBeatFx, false);
};

ArduinoDDJ400.beatFxChannel = function(_channel, control, value, _status, group) {
    if (value === 0x00) { return; }

    const enableChannel1 = control === 0x10 ? 1 : 0,
        enableChannel2 = control === 0x11 ? 1 : 0,
        enableMaster = control === 0x14 ? 1 : 0;

    engine.setValue(group, "group_[Channel1]_enable", enableChannel1);
    engine.setValue(group, "group_[Channel2]_enable", enableChannel2);
    engine.setValue(group, "group_[Master]_enable", enableMaster);
};

//
// Loop IN/OUT ADJUST
//

ArduinoDDJ400.toggleLoopAdjustIn = function(channel, _control, value, _status, group) {
    if (value === 0 || engine.getValue(group, "loop_enabled" === 0)) {
        return;
    }
    ArduinoDDJ400.loopAdjustIn[channel] = !ArduinoDDJ400.loopAdjustIn[channel];
    ArduinoDDJ400.loopAdjustOut[channel] = false;
};

ArduinoDDJ400.toggleLoopAdjustOut = function(channel, _control, value, _status, group) {
    if (value === 0 || engine.getValue(group, "loop_enabled" === 0)) {
        return;
    }
    ArduinoDDJ400.loopAdjustOut[channel] = !ArduinoDDJ400.loopAdjustOut[channel];
    ArduinoDDJ400.loopAdjustIn[channel] = false;
};

// Two signals are sent here so that the light stays lit/unlit in its shift state too
ArduinoDDJ400.setReloopLight = function(status, value) {
    midi.sendShortMsg(status, 0x4D, value);
    midi.sendShortMsg(status, 0x50, value);
};


ArduinoDDJ400.setLoopButtonLights = function(status, value) {
    [0x10, 0x11, 0x4E, 0x4C].forEach(function(control) {
        midi.sendShortMsg(status, control, value);
    });
};

ArduinoDDJ400.startLoopLightsBlink = function(channel, control, status, group) {
    let blink = 0x7F;

    ArduinoDDJ400.stopLoopLightsBlink(group, control, status);

    ArduinoDDJ400.timers[group][control] = engine.beginTimer(500, () => {
        blink = 0x7F - blink;

        // When adjusting the loop out position, turn the loop in light off
        if (ArduinoDDJ400.loopAdjustOut[channel]) {
            midi.sendShortMsg(status, 0x10, 0x00);
            midi.sendShortMsg(status, 0x4C, 0x00);
        } else {
            midi.sendShortMsg(status, 0x10, blink);
            midi.sendShortMsg(status, 0x4C, blink);
        }

        // When adjusting the loop in position, turn the loop out light off
        if (ArduinoDDJ400.loopAdjustIn[channel]) {
            midi.sendShortMsg(status, 0x11, 0x00);
            midi.sendShortMsg(status, 0x4E, 0x00);
        } else {
            midi.sendShortMsg(status, 0x11, blink);
            midi.sendShortMsg(status, 0x4E, blink);
        }
    });

};

ArduinoDDJ400.stopLoopLightsBlink = function(group, control, status) {
    ArduinoDDJ400.timers[group] = ArduinoDDJ400.timers[group] || {};

    if (ArduinoDDJ400.timers[group][control] !== undefined) {
        engine.stopTimer(ArduinoDDJ400.timers[group][control]);
    }
    ArduinoDDJ400.timers[group][control] = undefined;
    ArduinoDDJ400.setLoopButtonLights(status, 0x7F);
};

ArduinoDDJ400.loopToggle = function(value, group, control) {
    const status = group === "[Channel1]" ? 0x90 : 0x91,
        channel = group === "[Channel1]" ? 0 : 1;

    ArduinoDDJ400.setReloopLight(status, value ? 0x7F : 0x00);

    if (value) {
        ArduinoDDJ400.startLoopLightsBlink(channel, control, status, group);
    } else {
        ArduinoDDJ400.stopLoopLightsBlink(group, control, status);
        ArduinoDDJ400.loopAdjustIn[channel] = false;
        ArduinoDDJ400.loopAdjustOut[channel] = false;
    }
};

//
// CUE/LOOP CALL
//

ArduinoDDJ400.cueLoopCallLeft = function(_channel, _control, value, _status, group) {
    if (value) {
        engine.setValue(group, "loop_scale", 0.5);
    }
};

ArduinoDDJ400.cueLoopCallRight = function(_channel, _control, value, _status, group) {
    if (value) {
        engine.setValue(group, "loop_scale", 2.0);
    }
};

//
// BEAT SYNC
//
// Note that the controller sends different signals for a short press and a long
// press of the same button.
//

ArduinoDDJ400.syncPressed = function(channel, control, value, status, group) {
    if (engine.getValue(group, "sync_enabled") && value > 0) {
        engine.setValue(group, "sync_enabled", 0);
    } else {
        engine.setValue(group, "beatsync", value);
    }
};

ArduinoDDJ400.syncLongPressed = function(channel, control, value, status, group) {
    if (value) {
        engine.setValue(group, "sync_enabled", 1);
    }
};

ArduinoDDJ400.cycleTempoRange = function(_channel, _control, value, _status, group) {
    if (value === 0) { return; } // ignore release

    const currRange = engine.getValue(group, "rateRange");
    let idx = 0;

    for (let i = 0; i < this.tempoRanges.length; i++) {
        if (currRange === this.tempoRanges[i]) {
            idx = (i + 1) % this.tempoRanges.length;
            break;
        }
    }
    engine.setValue(group, "rateRange", this.tempoRanges[idx]);
};

//
// Jog wheels
//

ArduinoDDJ400.jogTurn = function(channel, _control, value, _status, group) {
    const deckNum = channel + 1;
    // wheel center at 64; <64 rew >64 fwd
    let newVal = value - 64;

    // loop_in / out adjust
    const loopEnabled = engine.getValue(group, "loop_enabled");
    if (loopEnabled > 0) {
        if (ArduinoDDJ400.loopAdjustIn[channel]) {
            newVal = newVal * ArduinoDDJ400.loopAdjustMultiply + engine.getValue(group, "loop_start_position");
            engine.setValue(group, "loop_start_position", newVal);
            return;
        }
        if (ArduinoDDJ400.loopAdjustOut[channel]) {
            newVal = newVal * ArduinoDDJ400.loopAdjustMultiply + engine.getValue(group, "loop_end_position");
            engine.setValue(group, "loop_end_position", newVal);
            return;
        }
    }

    if (engine.isScratching(deckNum)) {
        engine.scratchTick(deckNum, newVal);
    } else { // fallback
        engine.setValue(group, "jog", newVal * this.bendScale);
    }
};


ArduinoDDJ400.jogSearch = function(_channel, _control, value, _status, group) {
    const newVal = (value - 64) * ArduinoDDJ400.fastSeekScale;
    engine.setValue(group, "jog", newVal);
};

ArduinoDDJ400.jogTouch = function(channel, _control, value) {
    const deckNum = channel + 1;

    // skip while adjusting the loop points
    if (ArduinoDDJ400.loopAdjustIn[channel] || ArduinoDDJ400.loopAdjustOut[channel]) {
        return;
    }

    if (value !== 0 && this.vinylMode) {
        engine.scratchEnable(deckNum, 720, 33+1/3, this.alpha, this.beta);
    } else {
        engine.scratchDisable(deckNum);
    }
};

//
// Shift button
//

ArduinoDDJ400.shiftPressed = function(channel, _control, value, _status, _group) {
    ArduinoDDJ400.shiftButtonDown[channel] = value === 0x7F;
};


//
// Tempo sliders
//
// The tempo option in Mixxx's deck preferences determine whether down/up
// increases/decreases the rate. Therefore it must be inverted here so that the
// UI and the control sliders always move in the same direction.
//

ArduinoDDJ400.tempoSliderMSB = function(channel, control, value, status, group) {
    ArduinoDDJ400.highResMSB[group].tempoSlider = value;
};

ArduinoDDJ400.tempoSliderLSB = function(channel, control, value, status, group) {
    const fullValue = (ArduinoDDJ400.highResMSB[group].tempoSlider << 7) + value;

    engine.setValue(
        group,
        "rate",
        1 - (fullValue / 0x2000)
    );
};

//
// Beat Jump mode
//
// Note that when we increase/decrease the sizes on the pad buttons, we use the
// value of the first pad (0x21) as an upper/lower limit beyond which we don't
// allow further increasing/decreasing of all the values.
//

ArduinoDDJ400.beatjumpPadPressed = function(_channel, control, value, _status, group) {
    if (value === 0) {
        return;
    }
    engine.setValue(group, "beatjump_size", Math.abs(ArduinoDDJ400.beatjumpSizeForPad[control]));
    engine.setValue(group, "beatjump", ArduinoDDJ400.beatjumpSizeForPad[control]);
};

ArduinoDDJ400.increaseBeatjumpSizes = function(_channel, control, value, _status, group) {
    if (value === 0 || ArduinoDDJ400.beatjumpSizeForPad[0x21] * 16 > 16) {
        return;
    }
    Object.keys(ArduinoDDJ400.beatjumpSizeForPad).forEach(function(pad) {
        ArduinoDDJ400.beatjumpSizeForPad[pad] = ArduinoDDJ400.beatjumpSizeForPad[pad] * 16;
    });
    engine.setValue(group, "beatjump_size", ArduinoDDJ400.beatjumpSizeForPad[0x21]);
};

ArduinoDDJ400.decreaseBeatjumpSizes = function(_channel, control, value, _status, group) {
    if (value === 0 || ArduinoDDJ400.beatjumpSizeForPad[0x21] / 16 < 1/16) {
        return;
    }
    Object.keys(ArduinoDDJ400.beatjumpSizeForPad).forEach(function(pad) {
        ArduinoDDJ400.beatjumpSizeForPad[pad] = ArduinoDDJ400.beatjumpSizeForPad[pad] / 16;
    });
    engine.setValue(group, "beatjump_size", ArduinoDDJ400.beatjumpSizeForPad[0x21]);
};

//
// Sampler mode
//

ArduinoDDJ400.samplerPlayOutputCallbackFunction = function(value, group, _control) {
    if (value === 1) {
        const curPad = group.match(script.samplerRegEx)[1];
        ArduinoDDJ400.startSamplerBlink(
            0x97 + (curPad > 8 ? 2 : 0),
            0x30 + ((curPad > 8 ? curPad - 8 : curPad) - 1),
            group);
    }
};

ArduinoDDJ400.samplerPadPressed = function(_channel, _control, value, _status, group) {
    if (engine.getValue(group, "track_loaded")) {
        engine.setValue(group, "cue_gotoandplay", value);
    } else {
        engine.setValue(group, "LoadSelectedTrack", value);
    }
};

ArduinoDDJ400.samplerPadShiftPressed = function(_channel, _control, value, _status, group) {
    if (engine.getValue(group, "play")) {
        engine.setValue(group, "cue_gotoandstop", value);
    } else if (engine.getValue(group, "track_loaded")) {
        engine.setValue(group, "eject", value);
    }
};

ArduinoDDJ400.startSamplerBlink = function(channel, control, group) {
    let val = 0x7f;

    ArduinoDDJ400.stopSamplerBlink(channel, control);
    ArduinoDDJ400.timers[channel][control] = engine.beginTimer(250, () => {
        val = 0x7f - val;

        // blink the appropriate pad
        midi.sendShortMsg(channel, control, val);
        // also blink the pad while SHIFT is pressed
        midi.sendShortMsg((channel+1), control, val);

        const isPlaying = engine.getValue(group, "play") === 1;

        if (!isPlaying) {
            // kill timer
            ArduinoDDJ400.stopSamplerBlink(channel, control);
            // set the pad LED to ON
            midi.sendShortMsg(channel, control, 0x7f);
            // set the pad LED to ON while SHIFT is pressed
            midi.sendShortMsg((channel+1), control, 0x7f);
        }
    });
};

ArduinoDDJ400.stopSamplerBlink = function(channel, control) {
    ArduinoDDJ400.timers[channel] = ArduinoDDJ400.timers[channel] || {};

    if (ArduinoDDJ400.timers[channel][control] !== undefined) {
        engine.stopTimer(ArduinoDDJ400.timers[channel][control]);
        ArduinoDDJ400.timers[channel][control] = undefined;
    }
};

//
// Additional features
//

ArduinoDDJ400.toggleQuantize = function(_channel, _control, value, _status, group) {
    if (value) {
        script.toggleControl(group, "quantize");
    }
};

ArduinoDDJ400.quickJumpForward = function(_channel, _control, value, _status, group) {
    if (value) {
        engine.setValue(group, "beatjump", ArduinoDDJ400.quickJumpSize);
    }
};

ArduinoDDJ400.quickJumpBack = function(_channel, _control, value, _status, group) {
    if (value) {
        engine.setValue(group, "beatjump", -ArduinoDDJ400.quickJumpSize);
    }
};

//
// Shutdown
//

ArduinoDDJ400.shutdown = function() {
    if (ArduinoDDJ400.displayTimer) {
        engine.stopTimer(ArduinoDDJ400.displayTimer);
        ArduinoDDJ400.displayTimer = 0;
    }

    // reset vumeter
    ArduinoDDJ400.toggleLight(ArduinoDDJ400.lights.deck1.vuMeter, false);
    ArduinoDDJ400.toggleLight(ArduinoDDJ400.lights.deck2.vuMeter, false);

    // housekeeping
    // turn off all Sampler LEDs
    for (let i = 0; i <= 7; ++i) {
        midi.sendShortMsg(0x97, 0x30 + i, 0x00);    // Deck 1 pads
        midi.sendShortMsg(0x98, 0x30 + i, 0x00);    // Deck 1 pads with SHIFT
        midi.sendShortMsg(0x99, 0x30 + i, 0x00);    // Deck 2 pads
        midi.sendShortMsg(0x9A, 0x30 + i, 0x00);    // Deck 2 pads with SHIFT
    }
    // turn off all Hotcue LEDs
    for (let i = 0; i <= 7; ++i) {
        midi.sendShortMsg(0x97, 0x00 + i, 0x00);    // Deck 1 pads
        midi.sendShortMsg(0x98, 0x00 + i, 0x00);    // Deck 1 pads with SHIFT
        midi.sendShortMsg(0x99, 0x00 + i, 0x00);    // Deck 2 pads
        midi.sendShortMsg(0x9A, 0x00 + i, 0x00);    // Deck 2 pads with SHIFT
    }

    // turn off loop in and out lights
    ArduinoDDJ400.setLoopButtonLights(0x90, 0x00);
    ArduinoDDJ400.setLoopButtonLights(0x91, 0x00);

    // turn off reloop lights
    ArduinoDDJ400.setReloopLight(0x90, 0x00);
    ArduinoDDJ400.setReloopLight(0x91, 0x00);

    // stop any flashing lights
    ArduinoDDJ400.toggleLight(ArduinoDDJ400.lights.beatFx, false);
    ArduinoDDJ400.toggleLight(ArduinoDDJ400.lights.shiftBeatFx, false);
};
