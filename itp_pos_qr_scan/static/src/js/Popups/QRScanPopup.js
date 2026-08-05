/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class QRScanPopup extends Component {
    static template = "itp_pos_qr_scan.QRScanPopup";

    setup() {
        super.setup();
        this.popup = useService("popup");
        this.pos = useService("pos");

        this.state = useState({
            loading: true,
            active_camera: null,
            videoDevices: [],
            permissionState: "pending", // 'pending' | 'granted' | 'denied' | 'error'
            permissionError: "",
        });

        this.videoElement = useRef("preview");
        this.canvas = useRef("canvas");
        this.fileInput = useRef("fileInput");

        this.captureTimeout = 500;
        this.stream = null;
        this.gCtx = null;

        onMounted(() => {
            this.requestCameraPermission();
        });

        onWillUnmount(() => {
            this.stopCamera();
        });
    }

    get isBrowserSupported() {
        return Boolean(
            navigator.mediaDevices &&
            navigator.mediaDevices.enumerateDevices &&
            navigator.mediaDevices.getUserMedia
        );
    }

    stopCamera() {
        this.state.active_camera = false;
        if (this.stream) {
            try {
                this.stream.getTracks().forEach((track) => track.stop());
            } catch (_e) {}
            this.stream = null;
        }
    }

    async onClickCancel() {
        this.stopCamera();
        if (this.props && typeof this.props.close === "function") {
            this.props.close();
        } else if (this.props && typeof this.props.cancel === "function") {
            this.props.cancel();
        }
    }

    onTriggerFileInput() {
        if (this.fileInput && this.fileInput.el) {
            this.fileInput.el.click();
        }
    }

    onFileSelected(event) {
        const file = event.target.files && event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                this.initCanvas(800, 600);
                if (this.gCtx) {
                    this.gCtx.drawImage(img, 0, 0, 800, 600);
                    if (typeof window.qrcode !== "undefined") {
                        try {
                            window.qrcode.callback = (value) => this.read(value);
                            window.qrcode.decode();
                        } catch (err) {
                            console.error(err);
                            if (this.popup) {
                                this.popup.add("ErrorPopup", {
                                    title: "QR Decode Error",
                                    body: "Could not decode QR code from the uploaded image. Please ensure the QR code is clearly visible.",
                                });
                            }
                        }
                    }
                }
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    async requestCameraPermission() {
        if (!this.isBrowserSupported) {
            this.state.loading = false;
            this.state.permissionState = "error";
            this.state.permissionError = "Camera API is not supported by your browser or requires an HTTPS / localhost connection.";
            return;
        }

        this.state.loading = true;
        this.state.permissionError = "";

        try {
            // First prompt browser for camera permission
            const tempStream = await navigator.mediaDevices.getUserMedia({ audio: false, video: true });
            tempStream.getTracks().forEach((track) => track.stop());

            this.state.permissionState = "granted";
            const devices = await navigator.mediaDevices.enumerateDevices();
            const video_devices = devices.filter((d) => d.kind === "videoinput");

            this.state.videoDevices = video_devices;
            let deviceId = video_devices.length ? video_devices[0].deviceId : false;
            let facingMode = false;

            for (const device of video_devices) {
                if (device.label && device.label.toLowerCase().includes("back")) {
                    deviceId = device.deviceId;
                    facingMode = "environment";
                }
            }

            const active_camera_id = this.pos && this.pos.db ? this.pos.db.load("active_camera_id", false) : false;
            if (active_camera_id && video_devices.some((d) => d.deviceId === active_camera_id)) {
                deviceId = active_camera_id;
                facingMode = false;
            }

            this.state.loading = false;
            await this.startWebCam(deviceId, facingMode);
        } catch (error) {
            console.error("Camera permission error:", error);
            this.state.loading = false;
            this.state.permissionState = "denied";
            if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
                this.state.permissionError = "Camera permission was denied. Please allow camera access in your browser location bar or upload an image file.";
            } else if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
                this.state.permissionError = "No camera device was found on this system. You can upload a QR image file below.";
            } else {
                // Try starting webcam directly as fallback
                await this.startWebCam(false, false);
            }
        }
    }

    async onClickCameraButton(deviceId) {
        await this.startWebCam(deviceId, false);
        if (this.pos && this.pos.db) {
            this.pos.db.save("active_camera_id", deviceId);
        }
    }

    read(result) {
        if (this.pos && this.pos.debug) {
            console.log("QR scanned", result);
        }
        if (this.env && this.env.bus) {
            this.env.bus.trigger("qr_scanned", result);
        }
        this.stopCamera();
        if (this.props && typeof this.props.confirm === "function") {
            this.props.confirm({ confirmed: true, payload: result });
        } else if (this.props && typeof this.props.close === "function") {
            this.props.close();
        }
    }

    async startWebCam(deviceId, facingMode) {
        this.stopCamera();
        this.state.loading = false;
        this.initCanvas(800, 600);

        if (typeof window.qrcode !== "undefined") {
            window.qrcode.callback = (value) => this.read(value);
        }

        let stream = null;
        let lastError = null;

        const constraintsList = [];
        if (deviceId) {
            constraintsList.push({ video: { deviceId: { ideal: deviceId } }, audio: false });
        }
        if (facingMode) {
            constraintsList.push({ video: { facingMode: facingMode }, audio: false });
        }
        constraintsList.push({ video: { facingMode: "environment" }, audio: false });
        constraintsList.push({ video: true, audio: false }); // Universal fallback for PC, tablet & mobile integrated cameras

        for (const constraint of constraintsList) {
            try {
                stream = await navigator.mediaDevices.getUserMedia(constraint);
                if (stream) break;
            } catch (err) {
                lastError = err;
            }
        }

        if (stream) {
            this.stream = stream;
            this.state.permissionState = "granted";
            this.state.active_camera = deviceId || true;
            this.success(stream);
            setTimeout(() => this.captureToCanvas(), this.captureTimeout);
        } else {
            console.error("Camera start error:", lastError);
            this.state.permissionState = "error";
            this.state.permissionError = (lastError && lastError.message)
                ? lastError.message
                : "Could not start camera feed. Please allow camera access in your browser location bar or upload a QR image.";
        }
    }

    success(stream) {
        if (this.videoElement && this.videoElement.el) {
            this.videoElement.el.srcObject = stream;
            try {
                this.videoElement.el.play();
            } catch (_e) {}
        }
    }

    captureToCanvas() {
        if (!this.state.active_camera) return;

        try {
            if (this.gCtx && this.videoElement && this.videoElement.el) {
                this.gCtx.drawImage(this.videoElement.el, 0, 0, 800, 600);
                if (typeof window.qrcode !== "undefined") {
                    window.qrcode.decode();
                }
            }
        } catch (e) {
            // ignore frame decode error
        }
        if (this.state.active_camera) {
            setTimeout(() => this.captureToCanvas(), this.captureTimeout);
        }
    }

    initCanvas(w, h) {
        if (!this.canvas || !this.canvas.el) return;
        const gCanvas = this.canvas.el;
        gCanvas.style.width = w + "px";
        gCanvas.style.height = h + "px";
        gCanvas.width = w;
        gCanvas.height = h;
        const gCtx = gCanvas.getContext("2d");
        gCtx.clearRect(0, 0, w, h);
        this.gCtx = gCtx;
    }
}
