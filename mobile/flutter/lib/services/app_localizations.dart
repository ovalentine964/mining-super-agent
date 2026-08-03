import 'package:flutter/material.dart';

class AppLocalizations {
  final Locale locale;
  AppLocalizations(this.locale);

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const _localizedValues = <String, Map<String, String>>{
    'en': {
      'app_title': 'Sovereign Resource DAO',
      'identify': 'Identify Mineral',
      'prices': 'Market Prices',
      'reports': 'Reports',
      'settings': 'Settings',
      'take_photo': 'Take Photo',
      'analyzing': 'Analyzing mineral...',
    },
    'sw': {
      'app_title': 'Sovereign Resource DAO',
      'identify': 'Tambua Madini',
      'prices': 'Bei za Soko',
      'reports': 'Ripoti',
      'settings': 'Mipangilio',
      'take_photo': 'Piga Picha',
      'analyzing': 'Inachambua madini...',
    },
    'luo': {
      'app_title': 'Sovereign Resource DAO',
      'identify': 'Ngiyo Minera',
      'prices': 'Ngiyo Chiro',
      'reports': 'Ripoti',
      'settings': 'Mipangilio',
      'take_photo': 'Kweko Foto',
      'analyzing': 'Ng\'eyo minera...',
    },
    'luy': {
      'app_title': 'Sovereign Resource DAO',
      'identify': 'Khulia Minera',
      'prices': 'Ekhuli ya Soko',
      'reports': 'Ripoti',
      'settings': 'Mipangilio',
      'take_photo': 'Piga Picha',
      'analyzing': 'Ekhulia minera...',
    },
    'kam': {
      'app_title': 'Sovereign Resource DAO',
      'identify': 'Kiona Minera',
      'prices': 'Kiu ya Soko',
      'reports': 'Ripoti',
      'settings': 'Mipangilio',
      'take_photo': 'Piga Picha',
      'analyzing': 'Kiona minera...',
    },
  };

  String translate(String key) {
    return _localizedValues[locale.languageCode]?[key] ??
           _localizedValues['en']?[key] ??
           key;
  }
}
