import 'package:flutter_test/flutter_test.dart';
import 'package:maomao_client/presence/motion_classifier.dart';
import 'package:maomao_client/presence/motion_sampler.dart';

void main() {
  test('classifies from accumulated samples', () {
    final s = MotionSampler(window: 10);
    for (var i = 0; i < 20; i++) {
      s.addAccel(AccelSample(0, 0, i.isEven ? 9.81 : 13.81)); // std ~2 → walking
    }
    expect(s.currentMotion, MotionClassifier.walking);
  });

  test('window caps the buffer', () {
    final s = MotionSampler(window: 5);
    for (var i = 0; i < 50; i++) {
      s.addAccel(const AccelSample(0, 0, 9.81));
    }
    expect(s.currentMotion, MotionClassifier.stationary);
  });

  test('start subscribes to injected streams', () async {
    final s = MotionSampler(window: 100);
    final accel = Stream.fromIterable(
      [for (var i = 0; i < 20; i++) AccelSample(0, 0, i.isEven ? 9.81 : 17.81)],
    );
    s.start(accel);
    await Future<void>.delayed(const Duration(milliseconds: 20));
    expect(s.currentMotion, MotionClassifier.moving);
    await s.stop();
  });
}
