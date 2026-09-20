import 'dart:math' as math;

/// One accelerometer reading (m/s², including gravity).
class AccelSample {
  const AccelSample(this.x, this.y, this.z);
  final double x;
  final double y;
  final double z;
  double get magnitude => math.sqrt(x * x + y * y + z * z);
}

/// On-device motion classification (§15). The client only ever emits a
/// classification — never the raw sensor stream (§13). Heuristic based on the
/// standard deviation of accelerometer magnitude over a short window, with an
/// optional gyroscope hint to separate "handheld" (rotation, little motion)
/// from "stationary".
class MotionClassifier {
  const MotionClassifier({
    this.minSamples = 5,
    this.stationaryStd = 0.2,
    this.handheldStd = 1.0,
    this.walkingStd = 3.5,
    this.gyroHandheldRate = 0.35,
  });

  final int minSamples;
  final double stationaryStd;
  final double handheldStd;
  final double walkingStd;
  final double gyroHandheldRate;

  static const stationary = 'stationary';
  static const moving = 'moving';
  static const handheld = 'handheld';
  static const walking = 'walking';
  static const unknown = 'unknown';

  /// Standard deviation of accelerometer magnitude across [accel].
  static double magnitudeStd(List<AccelSample> accel) {
    if (accel.isEmpty) return 0;
    final mags = accel.map((s) => s.magnitude).toList();
    final mean = mags.reduce((a, b) => a + b) / mags.length;
    final variance =
        mags.map((m) => (m - mean) * (m - mean)).reduce((a, b) => a + b) / mags.length;
    return math.sqrt(variance);
  }

  /// Mean absolute gyroscope rate (rad/s) across [gyro].
  static double meanGyroRate(List<AccelSample> gyro) {
    if (gyro.isEmpty) return 0;
    return gyro.map((s) => s.magnitude).reduce((a, b) => a + b) / gyro.length;
  }

  String classify(List<AccelSample> accel, {List<AccelSample>? gyro}) {
    if (accel.length < minSamples) return unknown;
    final std = magnitudeStd(accel);

    if (std < stationaryStd) {
      // Very little linear motion: could still be held and rotated.
      if (gyro != null && meanGyroRate(gyro) >= gyroHandheldRate) return handheld;
      return stationary;
    }
    if (std < handheldStd) return handheld;
    if (std < walkingStd) return walking;
    return moving;
  }
}
