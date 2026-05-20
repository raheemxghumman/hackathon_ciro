import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import 'screens/input_screen.dart';
import 'theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.dark,
    statusBarBrightness: Brightness.light,
  ));
  runApp(const CIROApp());
}

class CIROApp extends StatelessWidget {
  const CIROApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ITLA',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.light,
        scaffoldBackgroundColor: CiroColors.canvas,
        primaryColor: CiroColors.brand,
        colorScheme: const ColorScheme.light(
          primary: CiroColors.brand,
          onPrimary: Colors.white,
          secondary: CiroColors.accent,
          onSecondary: Colors.white,
          surface: CiroColors.surface,
          onSurface: CiroColors.inkStrong,
        ),
        appBarTheme: AppBarTheme(
          backgroundColor: CiroColors.canvas,
          surfaceTintColor: CiroColors.canvas,
          elevation: 0,
          scrolledUnderElevation: 0,
          centerTitle: false,
          titleTextStyle: CiroType.h2(CiroColors.inkStrong),
          iconTheme: const IconThemeData(color: CiroColors.inkStrong),
          systemOverlayStyle: SystemUiOverlayStyle.dark,
        ),
        textTheme: GoogleFonts.poppinsTextTheme(ThemeData.light().textTheme).apply(
          bodyColor: CiroColors.inkBody,
          displayColor: CiroColors.inkStrong,
        ),
        dividerTheme: const DividerThemeData(
          color: CiroColors.hairline,
          thickness: 1,
          space: 1,
        ),
        snackBarTheme: SnackBarThemeData(
          backgroundColor: CiroColors.inkStrong,
          contentTextStyle: CiroType.bodyTight(Colors.white),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
      home: const InputScreen(),
    );
  }
}
