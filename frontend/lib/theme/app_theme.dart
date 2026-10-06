import 'package:flutter/material.dart';

/// Professional Financial Trading-Terminal Design System
/// Adheres strictly to the principles in apps.md:
/// - Information first, clean typography, neutral dark backgrounds
/// - Minimal decoration: no glowing effects, no neon, no robot/AI graphics
/// - Color is used strictly to communicate market state
class AppTheme {
  // --- Neutral Backgrounds & Surfaces (Terminal Palette) ---
  static const Color background = Color(0xFF0E1117);      // Deep neutral terminal background
  static const Color surface = Color(0xFF161922);         // Primary card / table row
  static const Color surfaceSubtle = Color(0xFF1D212C);   // Hover / active row highlight
  static const Color border = Color(0xFF252A36);          // Subtle 1px structural divider
  static const Color borderSubtle = Color(0xFF1B202A);    // Secondary divider

  // --- Typography Colors ---
  static const Color textPrimary = Color(0xFFE6E8EC);     // High-contrast clean white
  static const Color textSecondary = Color(0xFF9096A2);   // Clear neutral secondary
  static const Color textMuted = Color(0xFF626978);       // Subtle caption & labels

  // --- Market State Indicators (Financial Color Standards) ---
  static const Color upGreen = Color(0xFF26A69A);         // Clean financial green (positive / bull)
  static const Color downRed = Color(0xFFEF5350);         // Clean financial red (negative / bear)

  // --- Analysis Engine States (Non-distracting, Functional) ---
  static const Color validSetup = Color(0xFF26A69A);      // Emerald green
  static const Color potentialSetup = Color(0xFF42A5F5);  // Calm financial blue
  static const Color watch = Color(0xFFFFA726);           // Amber
  static const Color noSetup = Color(0xFF787F8D);         // Muted slate
  static const Color invalidated = Color(0xFFEF5350);     // Soft red

  // --- Primary UI Accents ---
  static const Color accent = Color(0xFF3875F6);          // Subtle terminal blue for active controls
  static const Color accentHover = Color(0xFF2C60D4);

  // --- Aliases for compatibility ---
  static const Color primary = accent;
  static const Color primaryLight = accentHover;
  static const Color surfaceLight = surfaceSubtle;

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: background,
      primaryColor: accent,
      cardColor: surface,
      dividerColor: border,
      colorScheme: const ColorScheme.dark(
        primary: accent,
        secondary: accentHover,
        surface: surface,
        error: downRed,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: background,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: textPrimary, size: 20),
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 16,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.2,
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: surface,
        selectedItemColor: textPrimary,
        unselectedItemColor: textMuted,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
        selectedLabelStyle: TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
        unselectedLabelStyle: TextStyle(fontSize: 11, fontWeight: FontWeight.w500),
      ),
      fontFamily: 'Roboto',
    );
  }

  static Color getStateColor(String state) {
    switch (state.toUpperCase()) {
      case 'VALID_SETUP':
      case 'VALID SETUP':
        return validSetup;
      case 'POTENTIAL_SETUP':
      case 'POTENTIAL SETUP':
        return potentialSetup;
      case 'WATCH':
        return watch;
      case 'INVALIDATED':
        return invalidated;
      default:
        return noSetup;
    }
  }

  static String getStateLabel(String state) {
    switch (state.toUpperCase()) {
      case 'VALID_SETUP':
        return 'VALID SETUP';
      case 'POTENTIAL_SETUP':
        return 'POTENTIAL SETUP';
      case 'WATCH':
        return 'WATCH';
      case 'INVALIDATED':
        return 'INVALIDATED';
      case 'NO_SETUP':
        return 'NO SETUP';
      default:
        return state.toUpperCase();
    }
  }
}
