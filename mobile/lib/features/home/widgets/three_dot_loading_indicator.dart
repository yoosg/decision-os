import 'dart:async';
import 'package:flutter/material.dart';

class ThreeDotLoadingIndicator extends StatefulWidget {
  const ThreeDotLoadingIndicator({super.key});

  @override
  State<ThreeDotLoadingIndicator> createState() => _ThreeDotLoadingIndicatorState();
}

class _ThreeDotLoadingIndicatorState extends State<ThreeDotLoadingIndicator>
    with TickerProviderStateMixin {
  late final List<AnimationController> _controllers;
  late final List<Animation<double>> _opacities;
  final List<Timer> _timers = [];

  @override
  void initState() {
    super.initState();
    _controllers = List.generate(
      3,
      (i) => AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 600),
      ),
    );
    _opacities = _controllers.map((c) {
      return Tween<double>(begin: 1.0, end: 0.3)
          .chain(CurveTween(curve: Curves.easeInOut))
          .animate(c);
    }).toList();

    for (var i = 0; i < 3; i++) {
      final timer = Timer(Duration(milliseconds: i * 200), () {
        if (mounted) _controllers[i].repeat(reverse: true);
      });
      _timers.add(timer);
    }
  }

  @override
  void dispose() {
    for (final t in _timers) {
      t.cancel();
    }
    for (final c in _controllers) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final disableAnimations = MediaQuery.of(context).disableAnimations;

    if (disableAnimations) {
      return const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('·', style: TextStyle(fontSize: 20)),
          SizedBox(width: 3),
          Text('·', style: TextStyle(fontSize: 20)),
          SizedBox(width: 3),
          Text('·', style: TextStyle(fontSize: 20)),
        ],
      );
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(3, (i) {
        return Padding(
          padding: EdgeInsets.only(left: i > 0 ? 3.0 : 0),
          child: FadeTransition(
            opacity: _opacities[i],
            child: const Text('·', style: TextStyle(fontSize: 20)),
          ),
        );
      }),
    );
  }
}
