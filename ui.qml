// ui.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: root
    visible: true
    width: 1380
    height: 860
    minimumWidth: 1120
    minimumHeight: 740
    title: "Audio Equalizer — FFT DSP Studio"
    color: "#09090B"

    // Desaturated / Muted shadcn/ui Tokens
    readonly property color bgCanvas:      "#09090B"
    readonly property color bgCard:        "#101013"
    readonly property color bgMuted:       "#18181C"
    readonly property color bgSubtle:      "#0B0B0E"
    readonly property color borderDefault: "#242429"
    readonly property color borderHover:   "#383842"
    readonly property color fgPrimary:     "#E4E4E7"
    readonly property color fgMuted:       "#9CA3AF"
    readonly property color fgSubtle:      "#6B7280"

    // Desaturated Signal Colors
    readonly property color toneSlateBlue: "#728CAB"
    readonly property color toneLavender:  "#8E7AB5"
    readonly property color toneSageGreen: "#689D8A"
    readonly property color toneWarmSand:  "#C29D68"
    readonly property color toneMutedRose: "#B86B77"

    FileDialog {
        id: wavDialog
        title: "Import WAV File"
        nameFilters: ["WAV Audio Files (*.wav *.WAV)"]
        onAccepted: if (backend) backend.importWavFile(selectedFile.toString())
    }

    component ShadcnButton: Rectangle {
        property string textLabel: ""
        property string variant: "outline"
        signal clicked()

        height: 34
        implicitWidth: labelItem.implicitWidth + 22
        radius: 6

        color: {
            if (variant === "primary") return ma.pressed ? "#C4C4C8" : (ma.containsMouse ? "#D4D4D8" : "#E4E4E7")
            if (variant === "destructive") return ma.pressed ? "#8C4A54" : (ma.containsMouse ? "#B86B77" : "#9E5863")
            return ma.pressed ? "#242429" : (ma.containsMouse ? "#18181C" : "transparent")
        }

        border.width: (variant === "primary" || variant === "destructive") ? 0 : 1
        border.color: ma.containsMouse ? root.borderHover : root.borderDefault

        Behavior on color { ColorAnimation { duration: 100 } }

        Text {
            id: labelItem
            anchors.centerIn: parent
            text: parent.textLabel
            color: parent.variant === "primary" ? "#09090B" : "#E4E4E7"
            font.pixelSize: 12
            font.weight: Font.Medium
        }

        MouseArea {
            id: ma
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: parent.clicked()
        }
    }

    component MiniBtn: Rectangle {
        property string txt: ""
        signal clicked()
        height: 22
        width: Math.max(24, mTxt.implicitWidth + 10)
        radius: 4
        color: mMa.containsMouse ? "#242429" : root.bgMuted
        border.color: root.borderDefault
        Text {
            id: mTxt
            anchors.centerIn: parent
            text: parent.txt
            color: root.fgPrimary
            font.pixelSize: 11
            font.weight: Font.DemiBold
        }
        MouseArea {
            id: mMa
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: parent.clicked()
        }
    }

    component InteractiveWaveCard: Rectangle {
        property string badgeText: ""
        property string cardTitle: ""
        property string playerKey: "input"
        property bool showWindowBox: false
        property color traceColor: root.toneSlateBlue
        property var wavePoints: []
        property real cursorInView: 0.0
        property real boxStartInView: 0.0
        property real boxWidthRatio: 0.05
        property real zoomLevel: 1.0
        property string timeText: "0.00s / 3.00s"
        property bool isPlayingThis: backend ? (backend.activePlayer === playerKey) : false

        signal scrubbed(real viewNorm)
        signal zoomStep(real factor)
        signal zoomReset()

        Layout.fillWidth: true
        Layout.fillHeight: true
        radius: 10
        color: root.bgCard
        border.color: root.borderDefault
        border.width: 1

        onWavePointsChanged: waveCanvas.requestPaint()

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Rectangle {
                    height: 26
                    width: 72
                    radius: 5
                    color: isPlayingThis ? traceColor : root.bgMuted
                    border.color: isPlayingThis ? traceColor : root.borderDefault
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: isPlayingThis ? "⏸ Pause" : "▶ Play"
                        color: isPlayingThis ? "#09090B" : root.fgPrimary
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: if (backend) backend.togglePlay(playerKey)
                    }
                }

                Rectangle {
                    height: 22
                    width: bdgTxt.implicitWidth + 14
                    radius: 5
                    color: Qt.rgba(traceColor.r, traceColor.g, traceColor.b, 0.14)
                    border.color: Qt.rgba(traceColor.r, traceColor.g, traceColor.b, 0.35)
                    border.width: 1
                    Text {
                        id: bdgTxt
                        anchors.centerIn: parent
                        text: badgeText
                        color: traceColor
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                }

                Text {
                    text: cardTitle
                    color: root.fgPrimary
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                }

                Item { Layout.fillWidth: true }

                RowLayout {
                    spacing: 4
                    Text {
                        text: "Zoom:"
                        color: root.fgSubtle
                        font.pixelSize: 11
                    }
                    MiniBtn {
                        txt: "−"
                        onClicked: zoomStep(0.5)
                    }
                    MiniBtn {
                        txt: zoomLevel.toFixed(1) + "×"
                        onClicked: zoomReset()
                    }
                    MiniBtn {
                        txt: "+"
                        onClicked: zoomStep(2.0)
                    }
                }

                Rectangle {
                    height: 22
                    width: tRead.implicitWidth + 14
                    radius: 4
                    color: root.bgMuted
                    border.color: root.borderDefault
                    Text {
                        id: tRead
                        anchors.centerIn: parent
                        text: timeText
                        color: root.fgMuted
                        font.pixelSize: 11
                    }
                }
            }

            Rectangle {
                id: viewportRect
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 7
                color: root.bgSubtle
                border.color: "#18181C"
                border.width: 1
                clip: true

                Canvas {
                    id: waveCanvas
                    anchors.fill: parent
                    anchors.margins: 6

                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)

                        var midY = height / 2

                        ctx.strokeStyle = "#141418"
                        ctx.lineWidth = 1
                        for (var c = 1; c < 10; c++) {
                            var gx = (c / 10) * width
                            ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, height); ctx.stroke()
                        }
                        ctx.strokeStyle = "#222228"
                        ctx.beginPath(); ctx.moveTo(0, midY); ctx.lineTo(width, midY); ctx.stroke()

                        if (wavePoints && wavePoints.length > 1) {
                            ctx.beginPath()
                            for (var i = 0; i < wavePoints.length; i++) {
                                var x = (i / (wavePoints.length - 1)) * width
                                var y = midY - (wavePoints[i] * (height * 0.43))
                                if (i === 0) ctx.moveTo(x, y)
                                else ctx.lineTo(x, y)
                            }
                            ctx.strokeStyle = traceColor
                            ctx.lineWidth = 1.8
                            ctx.stroke()

                            ctx.lineTo(width, midY)
                            ctx.lineTo(0, midY)
                            ctx.closePath()
                            ctx.fillStyle = Qt.rgba(traceColor.r, traceColor.g, traceColor.b, 0.14)
                            ctx.fill()
                        }
                    }
                }

                Rectangle {
                    id: stftWindowBox
                    visible: showWindowBox
                    y: 6
                    height: parent.height - 12
                    width: (parent.width - 12) * boxWidthRatio
                    x: 6 + boxStartInView * (parent.width - 12)
                    color: Qt.rgba(root.toneWarmSand.r, root.toneWarmSand.g, root.toneWarmSand.b, 0.12)
                    border.color: root.toneWarmSand
                    border.width: 1.5
                    radius: 3
                    clip: true

                    Rectangle {
                        x: parent.width * 0.5
                        y: 0
                        width: parent.width * 0.5
                        height: parent.height
                        color: Qt.rgba(root.toneLavender.r, root.toneLavender.g, root.toneLavender.b, 0.18)
                    }

                    Rectangle {
                        x: parent.width * 0.5
                        y: 0
                        width: 1.5
                        height: parent.height
                        color: root.toneLavender
                        opacity: 0.9
                    }
                }

                Item {
                    y: 4
                    height: parent.height - 8
                    width: 2
                    x: 6 + cursorInView * (parent.width - 12)

                    Rectangle {
                        anchors.fill: parent
                        color: "#E4E4E7"
                    }
                    Rectangle {
                        width: 10
                        height: 10
                        radius: 5
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: -2
                        color: "#E4E4E7"
                        border.color: "#09090B"
                        border.width: 1.5
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    function updateFromMouse(mx) {
                        var usableW = Math.max(1, width - 12)
                        var norm = Math.max(0.0, Math.min(1.0, (mx - 6) / usableW))
                        scrubbed(norm)
                    }
                    onPressed: (mouse) => updateFromMouse(mouse.x)
                    onPositionChanged: (mouse) => { if (pressed) updateFromMouse(mouse.x) }
                    onWheel: (wheel) => {
                        if (wheel.angleDelta.y > 0) zoomStep(1.5)
                        else if (wheel.angleDelta.y < 0) zoomStep(1.0 / 1.5)
                    }
                }
            }
        }
    }

    Connections {
        target: backend
        function onEqWaveUpdated() {
            eqSplineCanvas.requestPaint()
        }
        function onWindowFrameUpdated() {
            winFrameCanvas.requestPaint()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        // ================= TOP NAVBAR CARD =================
        Rectangle {
            Layout.fillWidth: true
            height: 62
            radius: 10
            color: root.bgCard
            border.color: root.borderDefault
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 18
                spacing: 10

                ColumnLayout {
                    spacing: 2
                    RowLayout {
                        spacing: 8
                        Rectangle {
                            width: 8; height: 8; radius: 4
                            color: (backend && backend.isRecording) ? root.toneMutedRose : root.toneSageGreen
                        }
                        Text {
                            text: "FFT Equalizer Studio"
                            color: root.fgPrimary
                            font.pixelSize: 15
                            font.weight: Font.Bold
                        }
                        Rectangle {
                            height: 20
                            width: dspBadge.implicitWidth + 12
                            radius: 5
                            color: root.bgMuted
                            border.color: root.borderDefault
                            Text {
                                id: dspBadge
                                anchors.centerIn: parent
                                text: "DSP Micro Project"
                                color: root.fgMuted
                                font.pixelSize: 11
                            }
                        }
                    }
                    Text {
                        text: backend ? backend.statusText : ""
                        color: root.fgMuted
                        font.pixelSize: 12
                    }
                }

                Item { Layout.fillWidth: true }

                ComboBox {
                    id: micSelect
                    Layout.preferredWidth: 230
                    height: 34
                    model: backend ? backend.micDeviceLabels : ["Default Mic (PipeWire / Pulse)"]
                    currentIndex: backend ? backend.defaultMicIndex : 0
                    onActivated: (idx) => { if (backend) backend.setMicDevice(idx) }

                    delegate: ItemDelegate {
                        width: micSelect.width
                        height: 32
                        contentItem: Text {
                            text: modelData
                            color: highlighted ? "#E4E4E7" : "#9CA3AF"
                            font.pixelSize: 12
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            color: highlighted ? "#242429" : "#101013"
                        }
                    }

                    contentItem: Text {
                        leftPadding: 12
                        rightPadding: 28
                        text: micSelect.displayText
                        font.pixelSize: 12
                        color: root.fgPrimary
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }

                    background: Rectangle {
                        implicitWidth: 220
                        implicitHeight: 34
                        color: root.bgMuted
                        border.color: micSelect.pressed ? root.borderHover : root.borderDefault
                        border.width: 1
                        radius: 6
                    }

                    popup: Popup {
                        y: micSelect.height + 4
                        width: micSelect.width
                        implicitHeight: contentItem.implicitHeight
                        padding: 1
                        contentItem: ListView {
                            clip: true
                            implicitHeight: contentHeight
                            model: micSelect.popup.visible ? micSelect.delegateModel : null
                            currentIndex: micSelect.highlightedIndex
                        }
                        background: Rectangle {
                            color: "#101013"
                            border.color: root.borderDefault
                            radius: 6
                        }
                    }
                }

                ShadcnButton {
                    property bool rec: backend ? backend.isRecording : false
                    textLabel: rec ? "⏹ Stop Rec" : "● Record Mic"
                    variant: "destructive"
                    onClicked: if (backend) backend.toggleRecording()
                }

                ShadcnButton {
                    textLabel: "Import WAV"
                    variant: "outline"
                    onClicked: wavDialog.open()
                }

                ShadcnButton {
                    textLabel: "Synth Wave"
                    variant: "outline"
                    onClicked: if (backend) backend.loadSyntheticSignal()
                }

                ShadcnButton {
                    textLabel: "Export WAV"
                    variant: "primary"
                    onClicked: if (backend) backend.exportEqualizedWav()
                }
            }
        }

        // ================= MAIN SPLIT WORKSPACE =================
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            // -------- LEFT CARD: 6-BAND SPLINE EQUALIZER (0% to 200%) --------
            Rectangle {
                Layout.preferredWidth: 570
                Layout.fillHeight: true
                radius: 10
                color: root.bgCard
                border.color: root.borderDefault
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            spacing: 2
                            Text {
                                text: "Parametric Frequency Response"
                                color: root.fgPrimary
                                font.pixelSize: 15
                                font.weight: Font.Bold
                            }
                            Text {
                                text: "Select a preset or drag control nodes vertically (0% to 200%)"
                                color: root.fgMuted
                                font.pixelSize: 12
                            }
                        }
                        Item { Layout.fillWidth: true }

                        // Current Preset Indicator Badge
                        Rectangle {
                            height: 24
                            width: presetBadgeTxt.implicitWidth + 16
                            radius: 6
                            color: root.bgMuted
                            border.color: root.borderDefault
                            Text {
                                id: presetBadgeTxt
                                anchors.centerIn: parent
                                text: "Preset: " + (backend ? backend.activePreset : "V-Shape")
                                color: root.toneWarmSand
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                            }
                        }
                    }

                    // EQUALIZER PRESETS BAR
                    Rectangle {
                        Layout.fillWidth: true
                        height: 34
                        radius: 7
                        color: root.bgMuted
                        border.color: root.borderDefault

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 3
                            spacing: 3

                            Repeater {
                                model: backend ? backend.presetNames : ["Flat 100%", "Bass Boost", "Treble", "Vocal", "V-Shape", "Low-Pass", "High-Pass"]

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    radius: 5
                                    property bool isCurrent: backend ? (backend.activePreset === modelData) : false
                                    color: isCurrent ? root.bgCanvas : (pMa.containsMouse ? "#202026" : "transparent")
                                    border.color: isCurrent ? root.toneSlateBlue : "transparent"
                                    border.width: 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData
                                        color: parent.isCurrent ? root.fgPrimary : root.fgMuted
                                        font.pixelSize: 11
                                        font.weight: parent.isCurrent ? Font.DemiBold : Font.Normal
                                    }

                                    MouseArea {
                                        id: pMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: if (backend) backend.applyPreset(modelData)
                                    }
                                }
                            }
                        }
                    }

                    // Band Gain % Badges
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Repeater {
                            model: 6
                            Item {
                                Layout.fillWidth: true
                                height: 24
                                Rectangle {
                                    anchors.centerIn: parent
                                    height: 22
                                    width: gTxt.implicitWidth + 14
                                    radius: 5
                                    property real g: (backend && backend.bandGains.length > index) ? backend.bandGains[index] : 100.0
                                    color: Math.abs(g - 100.0) < 0.5 ? root.bgMuted : (g > 100.0 ? Qt.rgba(root.toneSlateBlue.r, root.toneSlateBlue.g, root.toneSlateBlue.b, 0.18) : Qt.rgba(root.toneMutedRose.r, root.toneMutedRose.g, root.toneMutedRose.b, 0.18))
                                    border.color: Math.abs(g - 100.0) < 0.5 ? root.borderDefault : (g > 100.0 ? root.toneSlateBlue : root.toneMutedRose)
                                    border.width: 1
                                    Text {
                                        id: gTxt
                                        anchors.centerIn: parent
                                        text: Math.round(parent.g) + "%"
                                        color: Math.abs(parent.g - 100.0) < 0.5 ? root.fgMuted : root.fgPrimary
                                        font.pixelSize: 11
                                        font.weight: Font.DemiBold
                                    }
                                }
                            }
                        }
                    }

                    // INTERACTIVE SPLINE + SLIDER CANVAS (0% to 200%)
                    Rectangle {
                        id: eqGraphArea
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 8
                        color: root.bgSubtle
                        border.color: "#18181C"
                        border.width: 1

                        readonly property real padTop: 24
                        readonly property real padBot: 24
                        readonly property real usableH: height - padTop - padBot

                        Canvas {
                            id: eqSplineCanvas
                            anchors.fill: parent

                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.clearRect(0, 0, width, height)

                                if (!backend || !backend.bandGains || backend.bandGains.length < 6) return
                                var gains = backend.bandGains
                                var N = gains.length
                                var colW = width / N
                                var padTop = eqGraphArea.padTop
                                var usableH = eqGraphArea.usableH
                                var midY = padTop + usableH / 2 // 100% Unity Line

                                // Grid lines at 200%, 150%, 100%, 50%, 0%
                                var pctTicks = [200, 150, 100, 50, 0]
                                ctx.font = "11px sans-serif"
                                for (var t = 0; t < pctTicks.length; t++) {
                                    var gy = padTop + (1.0 - (pctTicks[t] / 200.0)) * usableH
                                    ctx.strokeStyle = pctTicks[t] === 100 ? "#27272D" : "#141418"
                                    ctx.lineWidth = pctTicks[t] === 100 ? 1.5 : 1.0
                                    ctx.beginPath()
                                    ctx.moveTo(0, gy)
                                    ctx.lineTo(width, gy)
                                    ctx.stroke()

                                    ctx.fillStyle = "#52525B"
                                    ctx.fillText(pctTicks[t] + "%", 10, gy - 5)
                                }

                                var pts = []
                                for (var i = 0; i < N; i++) {
                                    var cx = (i + 0.5) * colW
                                    var cy = padTop + (1.0 - (gains[i] / 200.0)) * usableH
                                    pts.push({x: cx, y: cy})

                                    ctx.strokeStyle = "#18181C"
                                    ctx.lineWidth = 5
                                    ctx.lineCap = "round"
                                    ctx.beginPath()
                                    ctx.moveTo(cx, padTop)
                                    ctx.lineTo(cx, padTop + usableH)
                                    ctx.stroke()

                                    ctx.strokeStyle = gains[i] >= 100.0 ? "#728CAB" : "#B86B77"
                                    ctx.lineWidth = 5
                                    ctx.beginPath()
                                    ctx.moveTo(cx, midY)
                                    ctx.lineTo(cx, cy)
                                    ctx.stroke()
                                }

                                ctx.beginPath()
                                ctx.moveTo(0, pts[0].y)
                                ctx.lineTo(pts[0].x, pts[0].y)

                                for (var j = 0; j < pts.length - 1; j++) {
                                    var p0 = j > 0 ? pts[j - 1] : pts[j]
                                    var p1 = pts[j]
                                    var p2 = pts[j + 1]
                                    var p3 = j < pts.length - 2 ? pts[j + 2] : p2

                                    var cp1x = p1.x + (p2.x - p0.x) / 6
                                    var cp1y = p1.y + (p2.y - p0.y) / 6
                                    var cp2x = p2.x - (p3.x - p1.x) / 6
                                    var cp2y = p2.y - (p3.y - p1.y) / 6

                                    ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y)
                                }
                                ctx.lineTo(width, pts[pts.length - 1].y)

                                ctx.strokeStyle = "#8CA3C0"
                                ctx.lineWidth = 2.6
                                ctx.stroke()

                                ctx.lineTo(width, midY)
                                ctx.lineTo(0, midY)
                                ctx.closePath()
                                var grad = ctx.createLinearGradient(0, padTop, 0, padTop + usableH)
                                grad.addColorStop(0.0, "rgba(114, 140, 171, 0.22)")
                                grad.addColorStop(0.5, "rgba(114, 140, 171, 0.02)")
                                grad.addColorStop(1.0, "rgba(184, 107, 119, 0.18)")
                                ctx.fillStyle = grad
                                ctx.fill()

                                for (var k = 0; k < pts.length; k++) {
                                    ctx.beginPath()
                                    ctx.arc(pts[k].x, pts[k].y, 7, 0, Math.PI * 2)
                                    ctx.fillStyle = "#09090B"
                                    ctx.fill()
                                    ctx.lineWidth = 2.5
                                    ctx.strokeStyle = "#E4E4E7"
                                    ctx.stroke()
                                }
                            }
                        }

                        RowLayout {
                            anchors.fill: parent
                            spacing: 0

                            Repeater {
                                model: 6

                                Item {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.SizeVerCursor

                                        function updateGainFromY(mouseY) {
                                            if (!backend) return
                                            var clampedY = Math.max(eqGraphArea.padTop, Math.min(eqGraphArea.padTop + eqGraphArea.usableH, mouseY))
                                            var norm = 1.0 - ((clampedY - eqGraphArea.padTop) / eqGraphArea.usableH)
                                            var pct = Math.round((norm * 200.0) / 5.0) * 5.0 // Snap to 5% steps
                                            backend.setBandGain(index, pct)
                                        }

                                        onPressed: (mouse) => updateGainFromY(mouse.y)
                                        onPositionChanged: (mouse) => {
                                            if (pressed) updateGainFromY(mouse.y)
                                        }
                                        onDoubleClicked: {
                                            if (backend) backend.setBandGain(index, 100.0)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Repeater {
                            model: 6
                            Text {
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignHCenter
                                text: (backend && backend.bandLabels.length > index) ? backend.bandLabels[index] : ""
                                color: root.fgPrimary
                                font.pixelSize: 12
                                font.weight: Font.Medium
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: root.borderDefault }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Window Function"
                            color: root.fgMuted
                            font.pixelSize: 13
                            font.weight: Font.Medium
                        }
                        Item { Layout.fillWidth: true }

                        Rectangle {
                            id: winTabs
                            property string selectedWin: "Hann"
                            height: 34
                            width: 270
                            radius: 7
                            color: root.bgMuted
                            border.color: root.borderDefault

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 3
                                spacing: 3
                                Repeater {
                                    model: ["Hann", "Hamming", "Rectangular"]
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        radius: 5
                                        property bool active: winTabs.selectedWin === modelData
                                        color: active ? root.bgCanvas : "transparent"
                                        border.color: active ? root.borderDefault : "transparent"

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData
                                            color: parent.active ? root.fgPrimary : root.fgMuted
                                            font.pixelSize: 12
                                            font.weight: parent.active ? Font.DemiBold : Font.Normal
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                winTabs.selectedWin = modelData
                                                if (backend) backend.setDspParams(fftTabs.selectedFft, modelData)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "FFT Frame Size"
                            color: root.fgMuted
                            font.pixelSize: 13
                            font.weight: Font.Medium
                        }
                        Item { Layout.fillWidth: true }

                        Rectangle {
                            id: fftTabs
                            property int selectedFft: 1024
                            height: 34
                            width: 270
                            radius: 7
                            color: root.bgMuted
                            border.color: root.borderDefault

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 3
                                spacing: 3
                                Repeater {
                                    model: [512, 1024, 2048]
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        radius: 5
                                        property bool active: fftTabs.selectedFft === modelData
                                        color: active ? root.bgCanvas : "transparent"
                                        border.color: active ? root.borderDefault : "transparent"

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.toString() + " pts"
                                            color: parent.active ? root.fgPrimary : root.fgMuted
                                            font.pixelSize: 12
                                            font.weight: parent.active ? Font.DemiBold : Font.Normal
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                fftTabs.selectedFft = modelData
                                                if (backend) backend.setDspParams(modelData, winTabs.selectedWin)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // -------- RIGHT COLUMN: 3 LIVE SIGNAL CARDS --------
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 14

                InteractiveWaveCard {
                    badgeText: "Input x[n]"
                    cardTitle: "Input Signal Timeline"
                    playerKey: "input"
                    showWindowBox: true
                    traceColor: root.toneSlateBlue
                    wavePoints: backend ? backend.inputWavePoints : []
                    cursorInView: backend ? backend.inputCursorInView : 0.0
                    boxStartInView: backend ? backend.windowBoxStartInView : 0.0
                    boxWidthRatio: backend ? backend.windowBoxWidthInView : 0.05
                    zoomLevel: backend ? backend.inputZoomLevel : 1.0
                    timeText: backend ? backend.inputTimeReadout : "0.00s / 3.00s"
                    onScrubbed: (viewNorm) => { if (backend) backend.seekInputInView(viewNorm) }
                    onZoomStep: (factor) => { if (backend) backend.zoomInput(factor) }
                    onZoomReset: () => { if (backend) backend.resetInputZoom() }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 10
                    color: root.bgCard
                    border.color: root.borderDefault
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Rectangle {
                                height: 22
                                width: wBdg.implicitWidth + 14
                                radius: 5
                                color: Qt.rgba(root.toneWarmSand.r, root.toneWarmSand.g, root.toneWarmSand.b, 0.14)
                                border.color: Qt.rgba(root.toneWarmSand.r, root.toneWarmSand.g, root.toneWarmSand.b, 0.4)
                                border.width: 1
                                Text {
                                    id: wBdg
                                    anchors.centerIn: parent
                                    text: "Window w[n] · x[n]"
                                    color: root.toneWarmSand
                                    font.pixelSize: 11
                                    font.weight: Font.DemiBold
                                }
                            }

                            Text {
                                text: "Discrete STFT Frame (" + winTabs.selectedWin + ", N=" + fftTabs.selectedFft + ")"
                                color: root.fgPrimary
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: backend ? backend.currentSampleRangeText : ""
                                color: root.toneWarmSand
                                font.pixelSize: 11
                                font.weight: Font.Medium
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 7
                            color: root.bgSubtle
                            border.color: "#18181C"
                            border.width: 1
                            clip: true

                            Canvas {
                                id: winFrameCanvas
                                anchors.fill: parent
                                anchors.margins: 6

                                property var framePts: backend ? backend.windowedFramePoints : []
                                property var envPts: backend ? backend.windowCurvePoints : []

                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)

                                    var midY = height / 2

                                    ctx.strokeStyle = "#141418"
                                    ctx.lineWidth = 1
                                    for (var c = 1; c < 10; c++) {
                                        var gx = (c / 10) * width
                                        ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, height); ctx.stroke()
                                    }
                                    ctx.strokeStyle = "#222228"
                                    ctx.beginPath(); ctx.moveTo(0, midY); ctx.lineTo(width, midY); ctx.stroke()

                                    ctx.fillStyle = Qt.rgba(root.toneLavender.r, root.toneLavender.g, root.toneLavender.b, 0.08)
                                    ctx.fillRect(width * 0.5, 0, width * 0.5, height)

                                    ctx.strokeStyle = root.toneLavender
                                    ctx.lineWidth = 1.5
                                    ctx.setLineDash([4, 4])
                                    ctx.beginPath()
                                    ctx.moveTo(width * 0.5, 0)
                                    ctx.lineTo(width * 0.5, height)
                                    ctx.stroke()
                                    ctx.setLineDash([])

                                    ctx.font = "10px sans-serif"
                                    ctx.fillStyle = root.toneLavender
                                    ctx.textAlign = "right"
                                    ctx.fillText("50% Hop Boundary (N/2) — Next Frame Starts Here", width - 8, 14)

                                    ctx.textAlign = "left"
                                    ctx.fillStyle = root.toneWarmSand
                                    ctx.fillText("Active Hop (0 .. N/2)", 8, 14)

                                    if (framePts && framePts.length > 1) {
                                        ctx.beginPath()
                                        for (var i = 0; i < framePts.length; i++) {
                                            var x = (i / (framePts.length)) * width
                                            var y = midY - (framePts[i] * (height * 0.43))
                                            if (i === 0) ctx.moveTo(x, y)
                                            else ctx.lineTo(x, y)
                                        }
                                        ctx.strokeStyle = root.toneLavender
                                        ctx.lineWidth = 2.0
                                        ctx.stroke()

                                        ctx.lineTo(width, midY)
                                        ctx.lineTo(0, midY)
                                        ctx.closePath()
                                        ctx.fillStyle = Qt.rgba(root.toneLavender.r, root.toneLavender.g, root.toneLavender.b, 0.14)
                                        ctx.fill()
                                    }

                                    if (envPts && envPts.length > 1) {
                                        ctx.beginPath()
                                        for (var j = 0; j < envPts.length; j++) {
                                            var wx = (j / (envPts.length - 1)) * width
                                            var wy = height - 6 - (envPts[j] * (height - 12))
                                            if (j === 0) ctx.moveTo(wx, wy)
                                            else ctx.lineTo(wx, wy)
                                        }
                                        ctx.strokeStyle = root.toneWarmSand
                                        ctx.lineWidth = 2.2
                                        ctx.stroke()
                                    }
                                }
                            }

                            Rectangle {
                                y: 6
                                height: parent.height - 12
                                width: 2
                                property real relInBox: backend
                                    ? Math.max(0.0, Math.min(1.0, (backend.inputCursorInView - backend.windowBoxStartInView) / Math.max(0.001, backend.windowBoxWidthInView)))
                                    : 0.0
                                x: 6 + relInBox * (parent.width - 12)
                                color: "#E4E4E7"
                                opacity: 0.85
                            }
                        }
                    }
                }

                InteractiveWaveCard {
                    badgeText: "Output y[n]"
                    cardTitle: "Equalized Output Timeline"
                    playerKey: "equalized"
                    showWindowBox: false
                    traceColor: root.toneSageGreen
                    wavePoints: backend ? backend.equalizedWavePoints : []
                    cursorInView: backend ? backend.eqCursorInView : 0.0
                    zoomLevel: backend ? backend.eqZoomLevel : 1.0
                    timeText: backend ? backend.eqTimeReadout : "0.00s / 3.00s"
                    onScrubbed: (viewNorm) => { if (backend) backend.seekEqInView(viewNorm) }
                    onZoomStep: (factor) => { if (backend) backend.zoomEq(factor) }
                    onZoomReset: () => { if (backend) backend.resetEqZoom() }
                }
            }
        }
    }
}
