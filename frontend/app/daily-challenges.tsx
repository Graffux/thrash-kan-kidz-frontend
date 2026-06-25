// Daily Challenges full-screen UI. Backend lives at:
//   GET  /api/users/{uid}/daily-challenges
//   POST /api/users/{uid}/daily-challenges/select   { challenge_id }
//   POST /api/users/{uid}/daily-challenges/claim
import RewardReveal from "../components/RewardReveal";
import React, { useEffect, useState, useCallback } from "react";
import {
  View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator, Alert,
} from "react-native";
import { router, Stack } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useApp } from "../src/context/AppContext";

const API = "https://thrash-kan-kidz-api.onrender.com";

type Reward = { coins: number; free_packs: number; wheel_tickets: number; bonus_card_id: string | null };
type Offering = {
  id: string; type: string; name: string; description: string; icon?: string;
  target: number; progress: number; is_complete: boolean; rewards: Reward;
};
type Payload = {
  date_utc: string; reset_at_utc: string;
  offerings: Offering[];
  selected_id: string | null;
  selected_progress: number; selected_target: number; selected_is_complete: boolean;
  claimed_at: string | null;
};

const ICON_FOR_TYPE: Record<string, any> = {
  open_packs: "cube",
  collect_variants: "sparkles",
  complete_trades: "people",
};

export default function DailyChallengesScreen() {
  const [rewardRevealVisible, setRewardRevealVisible] = useState(false);
  const [rewardRevealCard, setRewardRevealCard] = useState<any>(null);
  const { user, refreshData } = useApp();
  const [data, setData] = useState<Payload | null>(null);
  const [busy, setBusy] = useState(false);
  const [rewardRevealSummary, setRewardRevealSummary] = useState("");

  const load = useCallback(async () => {
    if (!user?.id) return;
    try {
      const r = await fetch(`${API}/api/users/${user.id}/daily-challenges`);
      if (r.ok) setData(await r.json());
    } catch {}
  }, [user?.id]);

  useEffect(() => { load(); }, [load]);

  const select = async (cid: string) => {
    if (!user?.id || busy) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/users/${user.id}/daily-challenges/select`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenge_id: cid }),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        Alert.alert("Can't pick that", e.detail || "Try again");
      } else {
        await load();
      }
    } finally { setBusy(false); }
  };

  const claim = async () => {
    if (!user?.id || busy) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/users/${user.id}/daily-challenges/claim`, { method: "POST" });
      const j = await r.json();
      if (!r.ok) {
        Alert.alert("Can't claim yet", j.detail || "Finish the challenge first");
      } else {
        const g = j.granted || {};
        const lines = [];
        if (g.coins) lines.push(`+${g.coins} coins`);
        if (g.free_packs) lines.push(`+${g.free_packs} free pack${g.free_packs > 1 ? "s" : ""}`);
        if (g.wheel_tickets) lines.push(`+${g.wheel_tickets} wheel ticket${g.wheel_tickets > 1 ? "s" : ""}`);
        if (g.bonus_card_id) {
  const cardName = g.bonus_card?.name || g.bonus_card_id;
  lines.push(`+1 RARE CARD: ${cardName}`);
}
        if (g.bonus_card) {
          setRewardRevealCard(g.bonus_card);
          setRewardRevealSummary(lines.join("\n"));
          setRewardRevealVisible(true);
        } else {
          Alert.alert("Reward claimed! \\m/", lines.join("\n"));
        }
        await refreshData?.();
        await load();
      }
    } finally { setBusy(false); }
  };

  if (!data) {
    return (
      <View style={styles.center}>
        <Stack.Screen options={{ headerShown: false }} />
        <ActivityIndicator color="#ffd24a" />
      </View>
    );
  }

  const claimed = !!data.claimed_at;
  const canClaim = data.selected_is_complete && !claimed;
  const selected = data.offerings.find(o => o.id === data.selected_id) || null;

  return (
    <View style={styles.screen}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="daily-back-btn">
          <Ionicons name="chevron-back" size={28} color="#ffd24a" />
        </Pressable>
        <Text style={styles.headerTitle}>DAILY CHALLENGES</Text>
        <View style={{ width: 28 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 80 }}>
        <Text style={styles.subhead}>
          {selected
            ? (claimed ? "Today's reward already claimed. Comes back at UTC midnight." : "Locked in. Slam it out:")
            : "Pick ONE challenge for today. Choice is locked until UTC midnight."}
        </Text>

        {data.offerings.map((o) => {
          const isSelected = o.id === data.selected_id;
          const disabled = !!data.selected_id && !isSelected;
          return (
            <Pressable
              key={o.id}
              testID={`challenge-card-${o.id}`}
              disabled={disabled || busy}
              onPress={() => !data.selected_id && select(o.id)}
              style={[
                styles.card,
                isSelected && styles.cardSelected,
                disabled && styles.cardDisabled,
              ]}
            >
              <View style={styles.cardHead}>
                <Ionicons name={ICON_FOR_TYPE[o.type] || "flash"} size={22} color="#ffd24a" />
                <Text style={styles.cardName}>{o.name}</Text>
                {isSelected && <Text style={styles.lockedTag}>PICKED</Text>}
              </View>
              <Text style={styles.cardDesc}>{o.description}</Text>

              <View style={styles.progressRow}>
                <View style={styles.progressBg}>
                  <View style={[
                    styles.progressFill,
                    { width: `${Math.min(100, (o.progress / o.target) * 100)}%` },
                  ]} />
                </View>
                <Text style={styles.progressText}>{o.progress}/{o.target}</Text>
              </View>

              <View style={styles.rewardRow}>
                {o.rewards.coins > 0 && <Text style={styles.rewardChip}>+{o.rewards.coins} 🪙</Text>}
                {o.rewards.free_packs > 0 && <Text style={styles.rewardChip}>+{o.rewards.free_packs} 📦</Text>}
                {o.rewards.wheel_tickets > 0 && <Text style={styles.rewardChip}>+{o.rewards.wheel_tickets} 🎡</Text>}
                {o.rewards.bonus_card_id && (
                  <Text style={[styles.rewardChip, styles.bonusChip]}>+ RARE CARD</Text>
                )}
              </View>
            </Pressable>
          );
        })}

        {selected && (
          <Pressable
            testID="claim-reward-btn"
            disabled={!canClaim || busy}
            onPress={claim}
            style={[styles.claimBtn, !canClaim && styles.claimBtnDisabled]}
          >
            <Text style={styles.claimBtnText}>
              {claimed ? "✓ CLAIMED" : canClaim ? "🎁 CLAIM REWARD" : `${data.selected_progress}/${data.selected_target} — keep slamming`}
            </Text>
          </Pressable>
        )}

        <Text style={styles.resetNote}>Resets at UTC midnight ({data.reset_at_utc.split("T")[1]?.slice(0, 5)} UTC).</Text>
      </ScrollView>

            <RewardReveal
        visible={rewardRevealVisible}
        title="DAILY REWARD UNLOCKED!"
        subtitle={rewardRevealSummary || "Daily Challenge Prize"}
        card={rewardRevealCard}
        theme="daily"
        onClose={() => {
          setRewardRevealVisible(false);
          setRewardRevealCard(null);
          setRewardRevealSummary("");
        }}
      />
 
          
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#0d0d0d" },
  center: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0d0d0d" },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: 12, paddingTop: 48, paddingBottom: 12,
    borderBottomWidth: 1, borderBottomColor: "#222",
  },
  headerTitle: { color: "#ffd24a", fontSize: 18, fontWeight: "900", letterSpacing: 1 },
  subhead: { color: "#aaa", fontSize: 13, marginBottom: 16 },
  card: {
    backgroundColor: "#1a1a1a", borderRadius: 12, padding: 16, marginBottom: 12,
    borderWidth: 1, borderColor: "#333",
  },
  cardSelected: { borderColor: "#ffd24a", borderWidth: 2, backgroundColor: "#1f1a0a" },
  cardDisabled: { opacity: 0.4 },
  cardHead: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 6 },
  cardName: { color: "#fff", fontSize: 16, fontWeight: "800", flex: 1 },
  lockedTag: {
    color: "#0d0d0d", backgroundColor: "#ffd24a",
    fontSize: 10, fontWeight: "900", paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4,
  },
  cardDesc: { color: "#bbb", fontSize: 13, marginBottom: 12 },
  progressRow: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 10 },
  progressBg: { flex: 1, height: 6, backgroundColor: "#333", borderRadius: 3, overflow: "hidden" },
  progressFill: { height: "100%", backgroundColor: "#3a7a3a" },
  progressText: { color: "#9fe39f", fontSize: 12, fontVariant: ["tabular-nums"], minWidth: 40, textAlign: "right" },
  rewardRow: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  rewardChip: { color: "#ffd24a", fontSize: 11, backgroundColor: "#2a2410", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 4, fontWeight: "700" },
  bonusChip: { backgroundColor: "#3a1a4a", color: "#e5b4ff" },
  claimBtn: {
    backgroundColor: "#3a7a3a", padding: 16, borderRadius: 10, alignItems: "center", marginTop: 12,
  },
  claimBtnDisabled: { backgroundColor: "#2a2a2a" },
  claimBtnText: { color: "#fff", fontSize: 15, fontWeight: "900", letterSpacing: 0.5 },
  rewardOverlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.88)", alignItems: "center", justifyContent: "center", padding: 20 },
  rewardModal: { width: "100%", maxWidth: 360, backgroundColor: "#16051f", borderColor: "#ffd24a", borderWidth: 3, borderRadius: 18, padding: 18, alignItems: "center" },
  rewardModalTitle: { color: "#ffd24a", fontSize: 26, fontWeight: "900", textAlign: "center", letterSpacing: 1 },
  rewardModalSub: { color: "#e5b4ff", fontSize: 13, fontWeight: "800", marginTop: 4, marginBottom: 12 },
  rewardModalCard: { width: 260, height: 370, marginVertical: 10 },
  rewardModalName: { color: "#fff", fontSize: 18, fontWeight: "900", textAlign: "center", marginBottom: 14 },
  rewardModalBtn: { backgroundColor: "#ffd24a", paddingHorizontal: 22, paddingVertical: 12, borderRadius: 10 },
  rewardModalBtnText: { color: "#0d0d0d", fontSize: 15, fontWeight: "900" },
  resetNote: { color: "#555", fontSize: 11, textAlign: "center", marginTop: 20 },
});
