import 'dart:async';

import 'motion_classifier.dart';

/// Maintains a rolling window of IMU samples and exposes the current motion
/// classification. The stream plumbing (sensors_plus) is injected via [start]
/// so the buffer/classification logic stays plugin-free and unit-testable.
class MotionSampler {
  MotionSampler({this.classifier = const MotionClassifier(), this.window = 50});

  final MotionClassifier classifier;
  final int window;
  final List<AccelSample> _accel = [];
  final List<AccelSample> _gyro = [];
  StreamSubscription<AccelSample>? _accelSub;
  StreamSubscription<AccelSample>? _gyroSub;

  void addAccel(AccelSample s) {
    _accel.add(s);
    if (_accel.length > window) _accel.removeAt(0);
  }

  void addGyro(AccelSample s) {
    _gyro.add(s);
    if (_gyro.length > window) _gyro.removeAt(0);
  }

  String get currentMotion => classifier.classify(
        List.of(_accel),
        gyro: _gyro.isEmpty ? null : List.of(_gyro),
      );

  void start(Stream<AccelSample> accel, {Stream<AccelSample>? gyro}) {
    _accelSub = accel.listen(addAccel);
    if (gyro != null) _gyroSub = gyro.listen(addGyro);
  }

  Future<void> stop() async {
    await _accelSub?.cancel();
    await _gyroSub?.cancel();
  }
}
