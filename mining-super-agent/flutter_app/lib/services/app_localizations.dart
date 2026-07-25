import 'package:flutter/material.dart';

/// Minimal localization delegate.
/// Loads translations from embedded maps (no external files needed for MVP).
class AppLocalizations {
  final Locale locale;
  AppLocalizations(this.locale);

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations) ??
        AppLocalizations(const Locale('sw'));
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  // Translation maps
  static final Map<String, Map<String, String>> _translations = {
    'sw': _swahili,
    'en': _english,
    'luo': _luo,
  };

  String _t(String key) {
    return _translations[locale.languageCode]?[key] ??
        _translations['en']?[key] ??
        key;
  }

  // ── App ──
  String get appTitle => _t('appTitle');
  String get welcomeMessage => _t('welcomeMessage');
  String get offlineMode => _t('offlineMode');

  // ── Home Screen ──
  String get photoAnalysis => _t('photoAnalysis');
  String get photoAnalysisDesc => _t('photoAnalysisDesc');
  String get priceCheck => _t('priceCheck');
  String get priceCheckDesc => _t('priceCheckDesc');
  String get myReports => _t('myReports');
  String get myReportsDesc => _t('myReportsDesc');
  String get settings => _t('settings');
  String get settingsDesc => _t('settingsDesc');
  String get pendingSync => _t('pendingSync');

  // ── Photo Screen ──
  String get takePhoto => _t('takePhoto');
  String get gallery => _t('gallery');
  String get takePhotoHint => _t('takePhotoHint');
  String get takePhotoSubhint => _t('takePhotoSubhint');
  String get analyze => _t('analyze');
  String get analyzing => _t('analyzing');
  String get analysisComplete => _t('analysisComplete');
  String get identifiedMineral => _t('identifiedMineral');
  String get rockType => _t('rockType');
  String get description => _t('description');
  String get confidence => _t('confidence');
  String get economicMineralFound => _t('economicMineralFound');
  String get analysisDisclaimer => _t('analysisDisclaimer');
  String get saveReport => _t('saveReport');
  String get reportSaved => _t('reportSaved');
  String get latitude => _t('latitude');
  String get longitude => _t('longitude');
  String get accuracy => _t('accuracy');
  String get gettingLocation => _t('gettingLocation');

  // ── Price Screen ──
  String get livePrices => _t('livePrices');
  String get updated => _t('updated');
  String get priceDisclaimer => _t('priceDisclaimer');
  String get retry => _t('retry');

  // ── Report Screen ──
  String get noReports => _t('noReports');
  String get noReportsHint => _t('noReportsHint');
  String get pendingAnalysis => _t('pendingAnalysis');
  String get view => _t('view');
  String get share => _t('share');
  String get delete => _t('delete');
  String get viewPdf => _t('viewPdf');
  String get deleteReport => _t('deleteReport');
  String get deleteReportConfirm => _t('deleteReportConfirm');
  String get cancel => _t('cancel');
  String get economicValue => _t('economicValue');
  String get economicYes => _t('economicYes');
  String get date => _t('date');
  String get reportWillAnalyze => _t('reportWillAnalyze');

  // ── Settings Screen ──
  String get language => _t('language');
  String get notifications => _t('notifications');
  String get enableNotifications => _t('enableNotifications');
  String get enableNotificationsDesc => _t('enableNotificationsDesc');
  String get dataUsage => _t('dataUsage');
  String get wifiOnly => _t('wifiOnly');
  String get wifiOnlyDesc => _t('wifiOnlyDesc');
  String get compressImages => _t('compressImages');
  String get compressImagesDesc => _t('compressImagesDesc');
  String get about => _t('about');
  String get aboutApp => _t('aboutApp');
  String get aboutDescription => _t('aboutDescription');
  String get aboutFeatures => _t('aboutFeatures');
  String get featureMineralId => _t('featureMineralId');
  String get featurePriceCheck => _t('featurePriceCheck');
  String get featureOffline => _t('featureOffline');
  String get featureReports => _t('featureReports');
  String get aboutDisclaimer => _t('aboutDisclaimer');
  String get help => _t('help');
  String get helpDesc => _t('helpDesc');
  String get termsOfService => _t('termsOfService');
  String get privacyPolicy => _t('privacyPolicy');
  String get close => _t('close');
  String get howToTakePhoto => _t('howToTakePhoto');
  String get howToTakePhotoAnswer => _t('howToTakePhotoAnswer');
  String get howToCheckPrices => _t('howToCheckPrices');
  String get howToCheckPricesAnswer => _t('howToCheckPricesAnswer');
  String get howToViewReports => _t('howToViewReports');
  String get howToViewReportsAnswer => _t('howToViewReportsAnswer');
  String get howOfflineWorks => _t('howOfflineWorks');
  String get howOfflineWorksAnswer => _t('howOfflineWorksAnswer');

  // ── Swahili translations ──
  static const Map<String, String> _swahili = {
    'appTitle': 'Mining Super-Agent',
    'welcomeMessage': 'Karibu! Chagua huduma',
    'offlineMode': 'Mtandao haupo — data imehifadhiwa',
    'photoAnalysis': 'Picha ya Mwamba',
    'photoAnalysisDesc': 'Piga picha uchambue madini',
    'priceCheck': 'Bei za Madini',
    'priceCheckDesc': 'Bei za dhahabu na shaba',
    'myReports': 'Ripoti Zangu',
    'myReportsDesc': 'Angalia ripoti zako',
    'settings': 'Mipangilio',
    'settingsDesc': 'Lugha na mipangilio',
    'pendingSync': 'data inasubiri kutumwa',
    'takePhoto': 'Piga Picha',
    'gallery': 'Galeri',
    'takePhotoHint': 'Piga picha ya mwamba au mchanga',
    'takePhotoSubhint': 'Picha itachambuliwa na AI',
    'analyze': 'Chambua Sasa',
    'analyzing': 'Inachambua… Tafadhali subiri',
    'analysisComplete': 'Uchambuzi Umekamilika',
    'identifiedMineral': 'Madini',
    'rockType': 'Aina ya Mwamba',
    'description': 'Maelezo',
    'confidence': 'Uhakika',
    'economicMineralFound': 'Madini ya thamani yamepatikana!',
    'analysisDisclaimer': 'Hii ni uchambuzi wa awali. Thibitisho na mtaalamu wa madini kabla ya maamuzi yoyote ya kifedha.',
    'saveReport': 'Hifadhi Ripoti',
    'reportSaved': 'Ripoti imehifadhiwa!',
    'latitude': 'Latitudo',
    'longitude': 'Longitudo',
    'accuracy': 'Usahihi',
    'gettingLocation': 'Inapata mahali…',
    'livePrices': 'Bei za Sasa',
    'updated': 'Imesasishwa',
    'priceDisclaimer': 'Bei ni za rejelea tu. Bei halisi zinaweza kutofautiana. Hakikisha bei kabla ya kuuza.',
    'retry': 'Jaribu Tena',
    'noReports': 'Hakuna Ripoti',
    'noReportsHint': 'Piga picha ya mwamba kuanza',
    'pendingAnalysis': 'Inasubiri Uchambuzi',
    'view': 'Angalia',
    'share': 'Shiriki',
    'delete': 'Futa',
    'viewPdf': 'Angalia PDF',
    'deleteReport': 'Futa Ripoti',
    'deleteReportConfirm': 'Una uhakika unataka kufuta ripoti hii?',
    'cancel': 'Ghairi',
    'economicValue': 'Thamani ya Kiuchumi',
    'economicYes': 'Ndio — madini ya thamani',
    'date': 'Tarehe',
    'reportWillAnalyze': 'Ripoti itachambuliwa mtandaoni unapounganishwa.',
    'language': 'Lugha',
    'notifications': 'Arifa',
    'enableNotifications': 'Washa Arifa',
    'enableNotificationsDesc': 'Pata arifa bei zinapobadilika',
    'dataUsage': 'Matumizi ya Data',
    'wifiOnly': 'WiFi Tu',
    'wifiOnlyDesc': 'Synchronize tu ukiwa na WiFi',
    'compressImages': 'Punguza Ukubwa wa Picha',
    'compressImagesDesc': 'Hifadhi data — picha ndogo',
    'about': 'Kuhusu',
    'aboutApp': 'Kuhusu Programu',
    'aboutDescription': 'Mining Super-Agent ni programu ya AI inayosaidia wachimbaji Kenya kupata taarifa sahihi za madini.',
    'aboutFeatures': 'Vipengele:',
    'featureMineralId': 'Utambuzi wa madini kwa picha',
    'featurePriceCheck': 'Bei za madini kwa wakati halisi',
    'featureOffline': 'Inafanya kazi bila mtandao',
    'featureReports': 'Ripoti za kitaalamu',
    'aboutDisclaimer': 'Programu hii ni zana ya msaada tu. Si mbadala wa ushauri wa kitaalamu wa kijiolojia. Daima thibitisha na mtaalamu kabla ya maamuzi ya kifedha.',
    'help': 'Msaada',
    'helpDesc': 'Jinsi ya kutumia programu',
    'termsOfService': 'Masharti ya Huduma',
    'privacyPolicy': 'Sera ya Faragha',
    'close': 'Funga',
    'howToTakePhoto': 'Jinsi ya kupiga picha?',
    'howToTakePhotoAnswer': 'Bofya "Piga Picha" kwenye ukurasa kuu. Piga picha ya mwamba au mchanga. Programu itachambua picha na kukupa taarifa.',
    'howToCheckPrices': 'Jinsi ya kuangalia bei?',
    'howToCheckPricesAnswer': 'Bofya "Bei za Madini" kwenye ukurasa kuu. Utaona bei za dhahabu, shaba, na madini mengine.',
    'howToViewReports': 'Jinsi ya kuangalia ripoti?',
    'howToViewReportsAnswer': 'Bofya "Ripoti Zangu" kwenye ukurasa kuu. Utaona ripoti zako zote zilizohifadhiwa.',
    'howOfflineWorks': 'Programu inafanyaje kazi bila mtandao?',
    'howOfflineWorksAnswer': 'Picha na data zinahifadhiwa kwenye simu yako. Unapounganisha na mtandao, data itatumwa kwa server kuchambuliwa.',
  };

  // ── English translations ──
  static const Map<String, String> _english = {
    'appTitle': 'Mining Super-Agent',
    'welcomeMessage': 'Welcome! Choose a service',
    'offlineMode': 'No connection — data saved locally',
    'photoAnalysis': 'Rock Photo',
    'photoAnalysisDesc': 'Take a photo to analyze minerals',
    'priceCheck': 'Mineral Prices',
    'priceCheckDesc': 'Gold, copper & rare earth prices',
    'myReports': 'My Reports',
    'myReportsDesc': 'View your analysis reports',
    'settings': 'Settings',
    'settingsDesc': 'Language & preferences',
    'pendingSync': 'items pending sync',
    'takePhoto': 'Take Photo',
    'gallery': 'Gallery',
    'takePhotoHint': 'Take a photo of rock or soil',
    'takePhotoSubhint': 'AI will analyze the image',
    'analyze': 'Analyze Now',
    'analyzing': 'Analyzing… Please wait',
    'analysisComplete': 'Analysis Complete',
    'identifiedMineral': 'Mineral',
    'rockType': 'Rock Type',
    'description': 'Description',
    'confidence': 'Confidence',
    'economicMineralFound': 'Economic mineral detected!',
    'analysisDisclaimer': 'This is a preliminary analysis. Confirm with a mining expert before making any financial decisions.',
    'saveReport': 'Save Report',
    'reportSaved': 'Report saved!',
    'latitude': 'Latitude',
    'longitude': 'Longitude',
    'accuracy': 'Accuracy',
    'gettingLocation': 'Getting location…',
    'livePrices': 'Live Prices',
    'updated': 'Updated',
    'priceDisclaimer': 'Prices are indicative only. Actual prices may vary. Verify prices before selling.',
    'retry': 'Retry',
    'noReports': 'No Reports',
    'noReportsHint': 'Take a rock photo to get started',
    'pendingAnalysis': 'Pending Analysis',
    'view': 'View',
    'share': 'Share',
    'delete': 'Delete',
    'viewPdf': 'View PDF',
    'deleteReport': 'Delete Report',
    'deleteReportConfirm': 'Are you sure you want to delete this report?',
    'cancel': 'Cancel',
    'economicValue': 'Economic Value',
    'economicYes': 'Yes — valuable mineral',
    'date': 'Date',
    'reportWillAnalyze': 'Report will be analyzed when you connect to the internet.',
    'language': 'Language',
    'notifications': 'Notifications',
    'enableNotifications': 'Enable Notifications',
    'enableNotificationsDesc': 'Get alerts when prices change',
    'dataUsage': 'Data Usage',
    'wifiOnly': 'WiFi Only',
    'wifiOnlyDesc': 'Sync only when on WiFi',
    'compressImages': 'Compress Images',
    'compressImagesDesc': 'Save data — smaller photos',
    'about': 'About',
    'aboutApp': 'About App',
    'aboutDescription': 'Mining Super-Agent is an AI-powered app that helps Kenyan miners get accurate mineral information.',
    'aboutFeatures': 'Features:',
    'featureMineralId': 'AI mineral identification from photos',
    'featurePriceCheck': 'Real-time mineral prices',
    'featureOffline': 'Works offline',
    'featureReports': 'Professional reports',
    'aboutDisclaimer': 'This app is an aid tool only. It is not a substitute for professional geological advice. Always verify with an expert before financial decisions.',
    'help': 'Help',
    'helpDesc': 'How to use the app',
    'termsOfService': 'Terms of Service',
    'privacyPolicy': 'Privacy Policy',
    'close': 'Close',
    'howToTakePhoto': 'How to take a photo?',
    'howToTakePhotoAnswer': 'Tap "Take Photo" on the home screen. Take a photo of rock or soil. The app will analyze it and give you information.',
    'howToCheckPrices': 'How to check prices?',
    'howToCheckPricesAnswer': 'Tap "Mineral Prices" on the home screen. You will see prices for gold, copper, and other minerals.',
    'howToViewReports': 'How to view reports?',
    'howToViewReportsAnswer': 'Tap "My Reports" on the home screen. You will see all your saved reports.',
    'howOfflineWorks': 'How does offline mode work?',
    'howOfflineWorksAnswer': 'Photos and data are saved on your phone. When you connect to the internet, data is sent to the server for analysis.',
  };

  // ── Luo translations (key strings, human-reviewed) ──
  static const Map<String, String> _luo = {
    'appTitle': 'Mining Super-Agent',
    'welcomeMessage': 'Oriti wuoyo! Yer karata',
    'offlineMode': 'WiFi pe — data niyo ka simu',
    'photoAnalysis': 'Kit Marith',
    'photoAnalysisDesc': 'Kuw marith mondo ong\'e minieri',
    'priceCheck': 'Nengo Minieri',
    'priceCheckDesc': 'Nengo dhahabu gi shaba',
    'myReports': 'Ripoti Jakwaro',
    'myReportsDesc': 'Ne ripoti jamar kanyakla',
    'settings': 'Tich',
    'settingsDesc': 'Dholuo gi tich mor',
    'pendingSync': 'data ni ng\'eyo oketni',
    'takePhoto': 'Kuw Marith',
    'gallery': 'Galeri',
    'takePhotoHint': 'Kuw marith mar thur gi luel',
    'takePhotoSubhint': 'AI ng\'olo marith',
    'analyze': 'Ong\'e Seche',
    'analyzing': 'Ng\'olo… Kwaiti dakika',
    'analysisComplete': 'Ng\'olo Otum',
    'identifiedMineral': 'Minieri',
    'rockType': 'Kit Thur',
    'description': 'Nyalore',
    'confidence': 'Thuolo',
    'economicMineralFound': 'Minieri mar thili e!',
    'analysisDisclaimer': 'Ng\'omo en ng\'olo machiegni. Confirm gi jatich minieri chiemb\'e ma olit gi kwany.',
    'saveReport': 'Gik Ripoti',
    'reportSaved': 'Ripoti ogikni!',
    'latitude': 'Latitudo',
    'longitude': 'Longitudo',
    'accuracy': 'Thuolo',
    'gettingLocation': 'Ngiyo place…',
    'livePrices': 'Nengo Kanisi',
    'updated': 'Oyudo',
    'priceDisclaimer': 'Nengo en rejelea matin. Nengo adiera maneu wuoyo. Confirm nengo chiemb\'e ma olit gi.',
    'retry': 'Tem Kaka',
    'noReports': 'Ripogi',
    'noReportsHint': 'Kuw marith mondo oket',
    'pendingAnalysis': 'Ng\'eyo Ng\'olo',
    'view': 'Ne',
    'share': 'Konyi',
    'delete': 'Golo',
    'viewPdf': 'Ne PDF',
    'deleteReport': 'Golo Ripoti',
    'deleteReportConfirm': 'Imiyo ni ogol ripotie?',
    'cancel': 'Chung\'a',
    'economicValue': 'Thili Mar Ngiyo',
    'economicYes': 'E — minieri mar thili',
    'date': 'Chieng\'',
    'reportWillAnalyze': 'Ripoti ng\'olo e gi internet.',
    'language': 'Dhok',
    'notifications': 'Loko',
    'enableNotifications': 'Ywe Loko',
    'enableNotificationsDesc': 'Gin loko nengo mondo wuoyo',
    'dataUsage': 'Tich Data',
    'wifiOnly': 'WiFi Keck',
    'wifiOnlyDesc': 'Sync ka en WiFi keck',
    'compressImages': 'Ket Marith Matin',
    'compressImagesDesc': 'Gik data — marith matin',
    'about': 'Makwach',
    'aboutApp': 'Makwach App',
    'aboutDescription': 'Mining Super-Agent en app mar AI makinde jaminieri Kenya mondo gino nyal ng\'e minieri.',
    'aboutFeatures': 'Tich:',
    'featureMineralId': 'Ng\'olo minieri gi marith',
    'featurePriceCheck': 'Nengo minieri kanisi',
    'featureOffline': 'Tich ka pe internet',
    'featureReports': 'Ripoti mar jatich',
    'aboutDisclaimer': 'App en tich machiegni. Pe en replace gi jatich minieri. Confirm gi jatich chiemb\'e ma olit gi kwany.',
    'help': 'Konyi',
    'helpDesc': 'Kaka itich app',
    'termsOfService': 'Tich Makwach',
    'privacyPolicy': 'Nyalo Private',
    'close': 'Chung\'a',
    'howToTakePhoto': 'Kaka akuw marith?',
    'howToTakePhotoAnswer': 'Dii "Kuw Marith" e screen mag home. Kuw marith mar thur gi luel. App ng\'olo.',
    'howToCheckPrices': 'Kaka ane nengo?',
    'howToCheckPricesAnswer': 'Dii "Nengo Minieri" e screen mag home. Ine nengo dhahabu gi shaba.',
    'howToViewReports': 'Kaka ane ripoti?',
    'howToViewReportsAnswer': 'Dii "Ripoti Jakwaro" e screen mag home. Ine ripoti jamar.',
    'howOfflineWorks': 'App tich kaka ka pe internet?',
    'howOfflineWorksAnswer': 'Marith gi data gik ka simu. Ka internet oduol, data oser gi server mondo ong\'e.',
  };
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  bool isSupported(Locale locale) {
    return ['sw', 'en', 'luo'].contains(locale.languageCode);
  }

  @override
  Future<AppLocalizations> load(Locale locale) async {
    return AppLocalizations(locale);
  }

  @override
  bool shouldReload(covariant LocalizationsDelegate<AppLocalizations> old) =>
      false;
}
