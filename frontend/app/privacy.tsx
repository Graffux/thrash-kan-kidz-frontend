import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

export default function PrivacyPolicyScreen() {
  const router = useRouter();
  const BACKGROUND_IMAGE = 'https://customer-assets.emergentagent.com/job_earn-cards/artifacts/zgy2com2_enhanced-1771247671181.jpg';

  const sections = [
    {
      title: 'Information We Collect',
      content: `When you use Thrash Kan Kidz, we collect the following information:

• Username: Used to identify your account and display in the app.
• Game Progress: Your card collection, coins, achievements, and login streaks.
• Purchase History: Records of in-app purchases for coin packages.

We do not collect personal information such as your real name, email address, or phone number unless you provide it voluntarily.`
    },
    {
      title: 'How We Use Your Information',
      content: `We use the information we collect to:

• Provide and maintain the game experience
• Track your progress and achievements
• Process in-app purchases
• Improve our services and fix bugs
• Prevent fraud and abuse`
    },
    {
      title: 'Data Storage & Security',
      content: `Your data is stored securely on our servers. We implement industry-standard security measures to protect your information from unauthorized access, alteration, or destruction.

Game progress is automatically saved to our servers when you play. You can delete your account and all associated data at any time through the Profile settings.`
    },
    {
      title: 'Third-Party Services',
      content: `We use the following third-party services:

• Stripe: For processing payments. Stripe's privacy policy applies to payment transactions.
• Expo: For app delivery and updates.

We do not sell your personal information to third parties.`
    },
    {
      title: 'Children\'s Privacy',
      content: `Thrash Kan Kidz is intended for users of all ages. We do not knowingly collect personal information from children under 13 without parental consent. If you believe we have collected information from a child under 13, please contact us.`
    },
    {
      title: 'Your Rights',
      content: `You have the right to:

• Access your data
• Request deletion of your account
• Opt out of promotional communications
• Request a copy of your data

To exercise these rights, please contact us through the app or at support@thrashkankidz.com.`
    },
    {
      title: 'Changes to This Policy',
      content: `We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new policy in the app. Your continued use of the app after changes constitutes acceptance of the updated policy.`
    },
    {
      title: 'Contact Us',
      content: `If you have questions about this Privacy Policy or our practices, please contact us at:

support@thrashkankidz.com`
    }
  ];

  return (
    <SafeAreaView style={styles.container}>
      <Image
        source={{ uri: BACKGROUND_IMAGE }}
        style={styles.backgroundImage}
        resizeMode="cover"
      />
      <View style={styles.overlay} />
      
      <View style={styles.header}>
        <TouchableOpacity 
          style={styles.backButton}
          onPress={() => router.back()}
        >
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Privacy Policy</Text>
        <View style={styles.placeholder} />
      </View>

      <ScrollView 
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.titleContainer}>
          <Text style={styles.mainTitle}>Privacy Policy</Text>
          <Text style={styles.lastUpdated}>Last Updated: February 2026</Text>
        </View>

        <View style={styles.introContainer}>
          <Text style={styles.introText}>
            Welcome to Thrash Kan Kidz! Your privacy is important to us. This Privacy Policy explains how we collect, use, and protect your information when you use our mobile card collecting game.
          </Text>
        </View>

        {sections.map((section, index) => (
          <View key={index} style={styles.section}>
            <Text style={styles.sectionTitle}>{section.title}</Text>
            <Text style={styles.sectionContent}>{section.content}</Text>
          </View>
        ))}

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            By using Thrash Kan Kidz, you agree to this Privacy Policy.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f1a',
  },
  backgroundImage: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: '100%',
    height: '100%',
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  placeholder: {
    width: 40,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  titleContainer: {
    marginBottom: 20,
  },
  mainTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFD700',
    marginBottom: 8,
  },
  lastUpdated: {
    fontSize: 14,
    color: '#888',
  },
  introContainer: {
    backgroundColor: 'rgba(255, 215, 0, 0.1)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
    borderLeftWidth: 3,
    borderLeftColor: '#FFD700',
  },
  introText: {
    fontSize: 15,
    color: '#ddd',
    lineHeight: 22,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 12,
  },
  sectionContent: {
    fontSize: 14,
    color: '#bbb',
    lineHeight: 22,
  },
  footer: {
    marginTop: 20,
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
  },
  footerText: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
    fontStyle: 'italic',
  },
});
