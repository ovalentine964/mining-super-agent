import 'package:flutter/material.dart';

/// Locale provider for language switching.
class LocaleProvider extends ChangeNotifier {
  Locale _locale = const Locale('sw');

  Locale get locale => _locale;

  void setLocale(Locale locale) {
    _locale = locale;
    notifyListeners();
  }
}
