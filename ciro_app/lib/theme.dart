import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class CiroColors {
  static const canvas = Color(0xFFFAF8F3);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceAlt = Color(0xFFF1EDE4);
  static const surfaceMuted = Color(0xFFF8F4ED);

  static const inkStrong = Color(0xFF1A1F2E);
  static const inkBody = Color(0xFF3D4456);
  static const inkMuted = Color(0xFF5A6478);
  static const inkSubtle = Color(0xFF8E96A8);
  static const hairline = Color(0xFFE5E0D5);
  static const hairlineSoft = Color(0xFFEFEAE0);

  static const brand = Color(0xFF2D5F4F);
  static const brandSoft = Color(0xFFE5EFE9);
  static const brandInk = Color(0xFF1F4538);

  static const accent = Color(0xFFE8845E);
  static const accentSoft = Color(0xFFFBE9DF);

  static const dataInk = Color(0xFF3A5876);
  static const dataSoft = Color(0xFFE3EAF2);

  // Severity / priority
  static const sevLow = Color(0xFF4A7C5A);
  static const sevLowSoft = Color(0xFFE6EFE6);
  static const sevMed = Color(0xFFC9962B);
  static const sevMedSoft = Color(0xFFFAF1D9);
  static const sevHigh = Color(0xFFCC5C3A);
  static const sevHighSoft = Color(0xFFFBE5DC);
  static const sevCritical = Color(0xFF8B2C2C);
  static const sevCriticalSoft = Color(0xFFF5DCDC);
}

class CiroShadow {
  static List<BoxShadow> card = const [
    BoxShadow(color: Color(0x0F000000), blurRadius: 18, offset: Offset(0, 4)),
    BoxShadow(color: Color(0x05000000), blurRadius: 1, offset: Offset(0, 1)),
  ];
  static List<BoxShadow> pop = const [
    BoxShadow(color: Color(0x18000000), blurRadius: 28, offset: Offset(0, 10)),
  ];
}

class CiroType {
  static TextStyle display(Color c) => GoogleFonts.poppins(
        color: c,
        fontSize: 26,
        fontWeight: FontWeight.w700,
        height: 1.15,
        letterSpacing: -0.4,
      );
  static TextStyle h1(Color c) => GoogleFonts.poppins(
        color: c,
        fontSize: 21,
        fontWeight: FontWeight.w700,
        height: 1.25,
        letterSpacing: -0.2,
      );
  static TextStyle h2(Color c) => GoogleFonts.poppins(
        color: c,
        fontSize: 17,
        fontWeight: FontWeight.w600,
        height: 1.3,
      );
  static TextStyle h3(Color c) => GoogleFonts.poppins(
        color: c,
        fontSize: 15,
        fontWeight: FontWeight.w600,
        height: 1.35,
      );
  static TextStyle body(Color c) => GoogleFonts.poppins(
        color: c,
        fontSize: 14.5,
        fontWeight: FontWeight.w400,
        height: 1.5,
      );
  static TextStyle bodyTight(Color c) => GoogleFonts.poppins(
        color: c,
        fontSize: 13.5,
        fontWeight: FontWeight.w400,
        height: 1.45,
      );
  static TextStyle small(Color c) => GoogleFonts.poppins(
        color: c,
        fontSize: 12.5,
        fontWeight: FontWeight.w400,
        height: 1.4,
      );
  static TextStyle caption(Color c) => GoogleFonts.poppins(
        color: c,
        fontSize: 11.5,
        fontWeight: FontWeight.w500,
        height: 1.3,
      );
  static TextStyle eyebrow(Color c) => GoogleFonts.spaceMono(
        color: c,
        fontSize: 10.5,
        fontWeight: FontWeight.w500,
        letterSpacing: 1.6,
      );
  static TextStyle mono(Color c, {double size = 12.5, FontWeight w = FontWeight.w500}) =>
      GoogleFonts.spaceMono(
        color: c,
        fontSize: size,
        fontWeight: w,
        letterSpacing: 0.2,
      );
  static TextStyle metric(Color c) => GoogleFonts.spaceMono(
        color: c,
        fontSize: 24,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.5,
      );
}

BoxDecoration ciroCard({
  Color? color,
  Color border = CiroColors.hairline,
  double radius = 16,
  List<BoxShadow>? shadow,
}) =>
    BoxDecoration(
      color: color ?? CiroColors.surface,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: border, width: 1),
      boxShadow: shadow ?? CiroShadow.card,
    );

class SectionLabel extends StatelessWidget {
  const SectionLabel(this.text, {super.key, this.color = CiroColors.inkSubtle, this.trailing});
  final String text;
  final Color color;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(child: Text(text, style: CiroType.eyebrow(color))),
        if (trailing != null) trailing!,
      ],
    );
  }
}

class Pill extends StatelessWidget {
  const Pill({
    super.key,
    required this.text,
    required this.color,
    this.background,
    this.borderColor,
    this.icon,
    this.dot = false,
    this.dense = false,
  });
  final String text;
  final Color color;
  final Color? background;
  final Color? borderColor;
  final IconData? icon;
  final bool dot;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: dense ? 8 : 10,
        vertical: dense ? 3 : 5,
      ),
      decoration: BoxDecoration(
        color: background ?? color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: borderColor ?? color.withValues(alpha: 0.35),
          width: 0.8,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (dot) ...[
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            ),
            const SizedBox(width: 6),
          ],
          if (icon != null) ...[
            Icon(icon, color: color, size: dense ? 11 : 13),
            const SizedBox(width: 4),
          ],
          Text(
            text,
            style: CiroType.mono(color, size: dense ? 10 : 11, w: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}
