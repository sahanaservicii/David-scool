package ru.homeguard.agent;

import android.app.Activity;
import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.ImageFormat;
import android.graphics.SurfaceTexture;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.media.Image;
import android.media.ImageReader;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Looper;
import android.util.Size;
import android.view.Surface;
import android.view.TextureView;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.nio.ByteBuffer;
import java.util.Arrays;

/** Scans the pairing QR shown by the parent console. No external dependencies. */
public class ScanActivity extends Activity {

    public static final String EXTRA_PAIRING = "pairing";
    private static final int REQ_CAMERA = 71;

    private TextureView preview;
    private TextView hint;
    private CameraManager manager;
    private String cameraId;
    private CameraDevice camera;
    private CameraCaptureSession session;
    private ImageReader reader;
    private HandlerThread bg;
    private Handler bgHandler;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private volatile boolean done;
    private volatile byte[] frame;
    private volatile int fw, fh;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE,
                WindowManager.LayoutParams.FLAG_SECURE);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(0xFF0E1320);

        preview = new TextureView(this);
        preview.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        root.addView(preview);

        hint = Ui.txt(this, "Наведите камеру на QR-код в консоли родителя. Держите ровно.",
                14, 0xFFFFFFFF, false);
        hint.setPadding(Ui.dp(this, 20), Ui.dp(this, 16), Ui.dp(this, 20), Ui.dp(this, 24));
        root.addView(hint, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        setContentView(root);

        bg = new HandlerThread("hg-qr");
        bg.start();
        bgHandler = new Handler(bg.getLooper());

        manager = (CameraManager) getSystemService(Context.CAMERA_SERVICE);
        try {
            cameraId = pickCamera();
        } catch (Exception e) {
            fail("Камера недоступна");
            return;
        }
        if (checkSelfPermission(android.Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{android.Manifest.permission.CAMERA}, REQ_CAMERA);
        } else {
            open();
        }
    }

    private String pickCamera() throws CameraAccessException {
        for (String id : manager.getCameraIdList()) {
            Integer facing = manager.getCameraCharacteristics(id)
                    .get(CameraCharacteristics.LENS_FACING);
            if (facing != null && facing == CameraCharacteristics.LENS_FACING_BACK) return id;
        }
        return manager.getCameraIdList().length > 0 ? manager.getCameraIdList()[0] : null;
    }

    @Override
    public void onRequestPermissionsResult(int req, String[] perms, int[] res) {
        super.onRequestPermissionsResult(req, perms, res);
        if (req == REQ_CAMERA) {
            if (res.length > 0 && res[0] == PackageManager.PERMISSION_GRANTED) open();
            else fail("Разрешите камеру в настройках");
        }
    }

    private final TextureView.SurfaceTextureListener surfaceListener =
            new TextureView.SurfaceTextureListener() {
        @Override
        public void onSurfaceTextureAvailable(SurfaceTexture st, int w, int h) {
            if (camera != null) startSession(w, h);
        }
        @Override public void onSurfaceTextureSizeChanged(SurfaceTexture st, int w, int h) {}
        @Override public boolean onSurfaceTextureDestroyed(SurfaceTexture st) { return true; }
        @Override public void onSurfaceTextureUpdated(SurfaceTexture st) {}
    };

    private void open() {
        preview.setSurfaceTextureListener(surfaceListener);
        if (preview.isAvailable()) {
            SurfaceTexture st = preview.getSurfaceTexture();
            startSession(preview.getWidth(), preview.getHeight());
        }
        try {
            manager.openCamera(cameraId, new CameraDevice.StateCallback() {
                @Override
                public void onOpened(CameraDevice c) {
                    camera = c;
                    ui.post(new Runnable() {
                        @Override public void run() {
                            if (preview.isAvailable()) {
                                startSession(preview.getWidth(), preview.getHeight());
                            }
                        }
                    });
                }
                @Override public void onDisconnected(CameraDevice c) { c.close(); }
                @Override public void onError(CameraDevice c, int e) {
                    fail("Ошибка камеры " + e);
                }
            }, ui);
        } catch (Exception e) {
            fail("Не удалось открыть камеру");
        }
    }

    private void startSession(int w, int h) {
        if (camera == null || done || reader != null) return;
        final int tw = w > 0 ? w : 720, th = h > 0 ? h : 1280;
        try {
            Size[] sizes = manager.getCameraCharacteristics(cameraId)
                    .get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
                    .getOutputSizes(ImageFormat.YUV_420_888);
            Size shot = pickSize(sizes, 1280);
            fw = shot.getWidth();
            fh = shot.getHeight();
            reader = ImageReader.newInstance(fw, fh, ImageFormat.YUV_420_888, 2);
            reader.setOnImageAvailableListener(new ImageReader.OnImageAvailableListener() {
                @Override
                public void onImageAvailable(ImageReader r) {
                    Image img = null;
                    try {
                        img = r.acquireLatestImage();
                        if (img == null || done) return;
                        byte[] gray = yPlane(img);
                        if (gray == null) return;
                        frame = gray;
                        bgHandler.post(analyze);
                    } catch (Exception ignored) {
                    } finally {
                        if (img != null) img.close();
                    }
                }
            }, bgHandler);

            final Surface previewSurface = new Surface(preview.getSurfaceTexture());
            camera.createCaptureSession(Arrays.asList(previewSurface, reader.getSurface()),
                    new CameraCaptureSession.StateCallback() {
                @Override
                public void onConfigured(CameraCaptureSession s) {
                    session = s;
                    try {
                        CaptureRequest.Builder rb = camera.createCaptureRequest(
                                CameraDevice.TEMPLATE_PREVIEW);
                        rb.addTarget(previewSurface);
                        rb.addTarget(reader.getSurface());
                        rb.set(CaptureRequest.CONTROL_AF_MODE,
                                CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
                        s.setRepeatingRequest(rb.build(), null, bgHandler);
                    } catch (Exception e) {
                        fail("Не удалось запустить превью");
                    }
                }
                @Override public void onConfigureFailed(CameraCaptureSession s) {
                    fail("Не удалось настроить камеру");
                }
            }, bgHandler);
        } catch (Exception e) {
            fail("Ошибка камеры");
        }
    }

    private Size pickSize(Size[] sizes, int target) {
        Size best = sizes[0];
        int diff = Integer.MAX_VALUE;
        for (Size s : sizes) {
            int d = Math.abs(s.getWidth() - target);
            if (d < diff) { diff = d; best = s; }
        }
        return best;
    }

    /** Extracts the Y (luminance) plane into a dense grayscale byte array. */
    private byte[] yPlane(Image img) {
        Image.Plane[] planes = img.getPlanes();
        if (planes == null || planes.length == 0) return null;
        Image.Plane y = planes[0];
        ByteBuffer buf = y.getBuffer();
        int rowStride = y.getRowStride();
        int pixelStride = y.getPixelStride();
        int w = img.getWidth(), h = img.getHeight();
        byte[] out = new byte[w * h];
        buf.rewind();
        for (int row = 0; row < h; row++) {
            int pos = row * rowStride;
            for (int col = 0; col < w; col++) {
                out[row * w + col] = buf.get(pos + col * pixelStride);
            }
        }
        return out;
    }

    private final Runnable analyze = new Runnable() {
        @Override
        public void run() {
            byte[] g = frame;
            if (done || g == null) return;
            String result = QrCodec.decodeImage(g, fw, fh);
            if (result != null && result.startsWith("hg1:")) {
                found(result);
            }
        }
    };

    private void found(final String text) {
        if (done) return;
        done = true;
        ui.post(new Runnable() {
            @Override public void run() {
                android.content.Intent i = new android.content.Intent();
                i.putExtra(EXTRA_PAIRING, text);
                setResult(RESULT_OK, i);
                finish();
            }
        });
    }

    private void fail(final String msg) {
        if (done) return;
        done = true;
        ui.post(new Runnable() {
            @Override public void run() {
                Ui.toast(ScanActivity.this, msg);
                setResult(RESULT_CANCELED);
                finish();
            }
        });
    }

    @Override
    protected void onDestroy() {
        done = true;
        try {
            if (session != null) session.close();
            if (camera != null) camera.close();
            if (reader != null) reader.close();
        } catch (Exception ignored) {}
        if (bg != null) bg.quit();
        super.onDestroy();
    }
}
