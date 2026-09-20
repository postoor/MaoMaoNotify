import 'package:flutter_test/flutter_test.dart';
import 'package:maomao_client/presence/motion_classifier.dart';

/// Build `count` samples whose magnitude alternates between two z values,
/// giving a magnitude std of |b-a|/2.
List<AccelSample> alternating(double a, double b, {int count = 20}) => [
      for (var i = 0; i < count; i++) AccelSample(0, 0, i.isEven ? a : b),
    ];

void main() {
  const c = MotionClassifier();

  test('magnitudeStd of alternating series is |b-a|/2', () {
    expect(MotionClassifier.magnitudeStd(alternating(9.81, 10.81)), closeTo(0.5, 1e-9));
  });

  test('too few samples → unknown', () {
    expect(c.classify(alternating(9.81, 13.81, count: 3)), MotionClassifier.unknown);
  });

  test('flat/at-rest → stationary', () {
    expect(c.classify(alternating(9.81, 9.81)), MotionClassifier.stationary);
  });

  test('small motion → handheld (std ~0.5)', () {
    expect(c.classify(alternating(9.81, 10.81)), MotionClassifier.handheld);
  });

  test('rhythmic moderate motion → walking (std ~2)', () {
    expect(c.classify(alternating(9.81, 13.81)), MotionClassifier.walking);
  });

  test('large motion → moving (std ~4)', () {
    expect(c.classify(alternating(9.81, 17.81)), MotionClassifier.moving);
  });

  test('still but rotating (gyro) → handheld', () {
    final gyro = [for (var i = 0; i < 20; i++) const AccelSample(0.4, 0, 0)];
    expect(c.classify(alternating(9.81, 9.81), gyro: gyro), MotionClassifier.handheld);
  });
}
