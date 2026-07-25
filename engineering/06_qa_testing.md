# 🧪 DeepMine QA & Testing Plan

**Author:** Engineering Council Member 6 — QA Lead  
**Date:** 2026-07-25  
**Stack:** Python (DeerFlow, FastAPI), Dart (Flutter), PostgreSQL  
**AI Models:** EfficientNet-B4, CLIP, Nemotron 3 Ultra, PennyLane  
**Users:** Miners in rural Kenya — **reliability is CRITICAL**  
**Budget:** $0 (all tools free/open-source)

---

## 1. Testing Strategy — The Quality Pyramid

### 1.1 Philosophy: Test What Kills People First

This isn't a social media app. If DeepMine misidentifies a mineral, a miner might:
- Waste weeks mining worthless rock
- Miss a gold deposit thinking it's pyrite
- Lose trust in technology entirely

**Priority order:**
1. **Correctness** — Mineral identification accuracy (lives & livelihoods depend on it)
2. **Reliability** — App works offline, syncs correctly, doesn't crash
3. **Usability** — Works in Swahili, works on cheap phones, works in bad lighting
4. **Security** — Protects miner data, prevents abuse
5. **Performance** — Fast enough to be useful in the field

### 1.2 Testing Layers

```
         ╱╲
        ╱  ╲        E2E Tests (~5% of tests)
       ╱    ╲       - Full mineral ID pipeline
      ╱──────╲      - Telegram bot conversations
     ╱        ╲     - Mobile app workflows
    ╱          ╲    - Offline→Online sync
   ╱ Integration ╲   Integration Tests (~15%)
  ╱    Tests      ╲  - API endpoints (FastAPI)
 ╱────────────────╲  - Database operations (PostgreSQL)
╱    Unit Tests     ╲ - Agent communication (DeerFlow)
╱   (~80% of tests)  ╲- Model inference pipelines
╱────────────────────╲
```

### 1.3 Test Types Matrix

| Type | Tool | Cost | Runs On | Frequency |
|------|------|------|---------|-----------|
| **Unit** | pytest, flutter_test | Free | Every commit | Always |
| **Integration** | pytest + testcontainers | Free | Every PR | Always |
| **E2E** | Playwright, Patrol (Flutter) | Free | Nightly | Daily |
| **Performance** | Locust, flutter_benchmark | Free | Weekly | Weekly |
| **Security** | Bandit, Trivy, OWASP ZAP | Free | Weekly | Weekly |
| **AI Accuracy** | Custom eval harness | Free | Per model change | Per release |
| **UAT** | Manual + feedback forms | Free | Per milestone | Manual |

---

## 2. Unit Testing — The Foundation

### 2.1 Python Backend (pytest)

**Framework:** pytest + pytest-asyncio + pytest-cov  
**Target Coverage:** 90% for critical paths, 75% overall

```python
# tests/test_mineral_identifier.py
import pytest
from deeepmine.identify import MineralIdentifier
from deeepmine.models.clip_model import CLIPClassifier

class TestMineralIdentifier:
    """Tests for the core mineral identification pipeline."""
    
    @pytest.fixture
    def identifier(self):
        return MineralIdentifier()
    
    @pytest.fixture
    def gold_sample_image(self):
        """Load test gold sample image."""
        return load_test_image("samples/gold_001.jpg")
    
    @pytest.fixture
    def pyrite_sample_image(self):
        """Load test pyrite sample image."""
        return load_test_image("samples/pyrite_001.jpg")
    
    def test_identify_gold_returns_gold(self, identifier, gold_sample_image):
        """GOLD STANDARD TEST — If this fails, everything stops."""
        result = identifier.identify(gold_sample_image)
        assert result.mineral == "gold"
        assert result.confidence >= 0.85
    
    def test_identify_pyrite_not_gold(self, identifier, pyrite_sample_image):
        """CRITICAL: Pyrite (fool's gold) must not be identified as gold."""
        result = identifier.identify(pyrite_sample_image)
        assert result.mineral != "gold", "Pyrite misidentified as gold — CRITICAL FAILURE"
    
    def test_confidence_threshold_rejects_low_quality(self, identifier):
        """Blurry/unclear images should return 'uncertain', not a guess."""
        blurry_image = load_test_image("samples/blurry_001.jpg")
        result = identifier.identify(blurry_image)
        assert result.mineral == "uncertain"
        assert result.confidence < 0.5
    
    def test_handles_corrupt_image(self, identifier):
        """Corrupted images must not crash the system."""
        corrupt_data = b"not an image"
        result = identifier.identify(corrupt_data)
        assert result.error is not None
        assert result.mineral is None


class TestNemotronChat:
    """Tests for the Nemotron 3 Ultra conversational AI."""
    
    def test_swahili_greeting(self, chat_agent):
        """Must understand basic Swahili greetings."""
        response = chat_agent.chat("Habari")
        assert response.language == "sw"
        assert "nzuri" in response.text.lower() or "habari" in response.text.lower()
    
    def test_mineral_question_in_swahili(self, chat_agent):
        response = chat_agent.chat("Je, hii ni dhahabu?")
        assert response.intent == "mineral_identification"
    
    def test_refuses_harmful_content(self, chat_agent):
        """Must refuse requests for illegal mining info."""
        response = chat_agent.chat("How do I mine in a protected area?")
        assert response.refused is True
```

```python
# tests/test_sync_engine.py
class TestOfflineSync:
    """Tests for offline data synchronization."""
    
    def test_queue_creates_when_offline(self, sync_engine):
        sync_engine.set_offline()
        sync_engine.queue_identification(sample_data)
        assert sync_engine.pending_count == 1
    
    def test_sync_flushes_queue_when_online(self, sync_engine):
        sync_engine.set_offline()
        sync_engine.queue_identification(sample_data)
        sync_engine.queue_identification(sample_data2)
        sync_engine.set_online()
        result = sync_engine.sync()
        assert result.synced == 2
        assert sync_engine.pending_count == 0
    
    def test_conflict_resolution_latest_wins(self, sync_engine):
        """When same record modified offline by multiple sessions."""
        sync_engine.set_offline()
        sync_engine.update_record("rec_1", {"status": "gold"}, timestamp=100)
        sync_engine.update_record("rec_1", {"status": "pyrite"}, timestamp=200)
        sync_engine.set_online()
        synced = sync_engine.sync()
        assert synced.get_record("rec_1").status == "pyrite"
    
    def test_sync_survives_network_flap(self, sync_engine):
        """Network drops mid-sync shouldn't corrupt data."""
        sync_engine.set_offline()
        for i in range(100):
            sync_engine.queue_identification(make_sample(i))
        sync_engine.set_online()
        # Simulate network drop after 50 synced
        sync_engine.simulate_network_drop(after_records=50)
        result = sync_engine.sync()  # Should retry remaining
        assert result.synced == 100
        assert result.errors == 0
```

### 2.2 Flutter Mobile App (flutter_test)

**Framework:** flutter_test + mockito + bloc_test  
**Target Coverage:** 85% for business logic, 70% for UI

```dart
// test/blocs/mineral_bloc_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:mockito/mockito.dart';
import 'package:deepmine/blocs/mineral_bloc.dart';

void main() {
  group('MineralBloc', () {
    late MineralBloc bloc;
    late MockMineralRepository mockRepo;

    setUp(() {
      mockRepo = MockMineralRepository();
      bloc = MineralBloc(repository: mockRepo);
    });

    blocTest<MineralBloc, MineralState>(
      'emits [Loading, Loaded] when identification succeeds',
      build: () {
        when(mockRepo.identify(any)).thenAnswer(
          (_) async => MineralResult(mineral: 'gold', confidence: 0.92),
        );
        return bloc;
      },
      act: (bloc) => bloc.add(IdentifyMineral(imagePath: 'test.jpg')),
      expect: () => [
        isA<MineralLoading>(),
        isA<MineralLoaded>().having(
          (s) => s.result.mineral, 'mineral', 'gold',
        ),
      ],
    );

    blocTest<MineralBloc, MineralState>(
      'emits [Loading, Error] when offline and no cache',
      build: () {
        when(mockRepo.identify(any)).thenThrow(OfflineException());
        when(mockRepo.getCachedResult(any)).thenReturn(null);
        return bloc;
      },
      act: (bloc) => bloc.add(IdentifyMineral(imagePath: 'test.jpg')),
      expect: () => [
        isA<MineralLoading>(),
        isA<MineralError>().having(
          (s) => s.message, 'message', contains('offline'),
        ),
      ],
    );
  });
}

// test/widgets/camera_test.dart
void main() {
  testWidgets('Camera button triggers image capture', (tester) async {
    await tester.pumpWidget(MaterialApp(home: CameraScreen()));
    
    await tester.tap(find.byIcon(Icons.camera_alt));
    await tester.pumpAndSettle();
    
    expect(find.byType(ImagePreview), findsOneWidget);
  });

  testWidgets('Low light warning appears in dark conditions', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: CameraScreen(brightness: 0.1), // Simulate low light
    ));
    
    expect(find.text('More light needed'), findsOneWidget);
    expect(find.byIcon(Icons.wb_sunny), findsOneWidget);
  });
}
```

### 2.3 Database Tests (PostgreSQL)

```python
# tests/test_database.py
import pytest
from sqlalchemy import create_engine
from deeepmine.db import Base, MineralRecord, User

@pytest.fixture
def test_db():
    """Create a fresh test database for each test."""
    engine = create_engine("postgresql://test:test@localhost:5432/deeepmine_test")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

class TestMineralRecords:
    def test_create_record(self, test_db):
        record = MineralRecord(
            user_id="miner_001",
            mineral="gold",
            confidence=0.92,
            latitude=-1.2921,
            longitude=36.8219,
        )
        test_db.add(record)
        test_db.commit()
        
        saved = test_db.query(MineralRecord).first()
        assert saved.mineral == "gold"
        assert saved.confidence == 0.92
    
    def test_geospatial_query(self, test_db):
        """Find minerals within 10km radius."""
        # Seed test data
        test_db.add(MineralRecord(mineral="gold", lat=-1.29, lon=36.82))
        test_db.add(MineralRecord(mineral="gold", lat=-1.30, lon=36.83))
        test_db.add(MineralRecord(mineral="pyrite", lat=-5.00, lon=40.00))  # Far away
        test_db.commit()
        
        nearby = find_minerals_within_radius(
            test_db, center=(-1.29, 36.82), radius_km=10
        )
        assert len(nearby) == 2
        assert all(r.mineral == "gold" for r in nearby)
```

---

## 3. Integration Testing — How Things Connect

### 3.1 API Integration Tests

```python
# tests/integration/test_api.py
import pytest
from httpx import AsyncClient
from deeepmine.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c

class TestIdentifyEndpoint:
    async def test_identify_returns_result(self, client):
        with open("tests/fixtures/gold_sample.jpg", "rb") as f:
            response = await client.post(
                "/api/v1/identify",
                files={"image": ("gold.jpg", f, "image/jpeg")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["mineral"] in ["gold", "pyrite", "quartz", "uncertain"]
        assert 0 <= data["confidence"] <= 1
    
    async def test_identify_rejects_non_image(self, client):
        response = await client.post(
            "/api/v1/identify",
            files={"image": ("test.txt", b"not an image", "text/plain")},
        )
        assert response.status_code == 422
    
    async def test_identify_rate_limit(self, client):
        """Prevent abuse — max 100 requests per hour per user."""
        for _ in range(101):
            response = await client.post("/api/v1/identify", ...)
        assert response.status_code == 429

class TestTelegramBotIntegration:
    async def test_photo_message_triggers_identification(self, bot_client):
        """Simulate Telegram photo message flow."""
        update = make_telegram_photo_update(photo_path="gold_sample.jpg")
        response = await bot_client.post("/webhook/telegram", json=update)
        assert response.status_code == 200
        
        sent_message = get_last_sent_message()
        assert "gold" in sent_message.text.lower()
        assert "confidence" in sent_message.text.lower()
    
    async def test_text_message_swahili(self, bot_client):
        update = make_telegram_text_update("Habari, hii ni dhahabu?")
        response = await bot_client.post("/webhook/telegram", json=update)
        assert response.status_code == 200
```

### 3.2 Agent Communication Tests (DeerFlow)

```python
# tests/integration/test_agents.py
class TestAgentPipeline:
    async def test_coordinator_delegates_to_identifier(self):
        """Coordinator agent should route image tasks to identifier."""
        task = Task(type="identify", image=sample_image)
        result = await coordinator_agent.process(task)
        assert result.agent_used == "mineral_identifier"
    
    async def test_identifier_fallback_to_clip(self):
        """If EfficientNet fails, fall back to CLIP."""
        with mock_efficientnet_failure():
            result = await identifier_agent.identify(sample_image)
            assert result.model_used == "clip"
            assert result.fallback is True
    
    async def test_report_agent_generates_summary(self):
        result = await report_agent.generate(
            mineral="gold",
            location="Kisumu",
            confidence=0.92,
        )
        assert result.summary is not None
        assert len(result.summary) > 50
```

---

## 4. End-to-End Testing — Full User Journeys

### 4.1 E2E Test Scenarios

| Scenario | Priority | Platform | Description |
|----------|----------|----------|-------------|
| **Identify gold from photo** | P0 | Telegram + Mobile | Photo → AI → Result |
| **Offline identify + sync** | P0 | Mobile | Take photo offline → sync later |
| **Swahili conversation** | P0 | Telegram | Full chat in Swahili |
| **Multi-photo batch** | P1 | Mobile | Upload 10 photos at once |
| **Share results** | P1 | Mobile | Share via WhatsApp/SMS |
| **View history** | P2 | Mobile + Web | Browse past identifications |
| **Report suspicious activity** | P2 | Mobile | Flag environmental concerns |

### 4.2 E2E Test Implementation

```python
# tests/e2e/test_full_identification_flow.py
import pytest
from playwright.async_api import async_playwright

class TestFullIdentificationFlow:
    """E2E: User takes photo → gets mineral identification."""
    
    async def test_telegram_photo_identification(self):
        """Full flow: Send photo to Telegram bot, receive identification."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Navigate to Telegram Web
            await page.goto("https://web.telegram.org")
            await login_telegram(page)
            
            # Find DeepMine bot
            await page.click('[data-testid="search"]')
            await page.fill('input', 'DeepMine Bot')
            await page.click('.search-result')
            
            # Send photo
            await page.set_input_files(
                'input[type="file"]',
                'tests/fixtures/gold_sample.jpg'
            )
            await page.press('input[type="file"]', 'Enter')
            
            # Wait for bot response (max 30s — model inference)
            await page.wait_for_selector('.message-content:has-text("gold")', timeout=30000)
            
            response = await page.text_content('.message-content:last-child')
            assert "gold" in response.lower()
            assert "confidence" in response.lower() or "%" in response
    
    async def test_mobile_offline_identification(self):
        """E2E: Take photo offline, verify sync when back online."""
        device = await launch_flutter_test_device()
        
        # Go offline
        await device.set_network(False)
        
        # Take photo
        await device.tap(find.byIcon(Icons.camera))
        await device.tap(find.byIcon(Icons.camera_alt))  # Capture
        
        # Verify offline indicator
        expect(find.text('Saved offline')).exists()
        
        # Go online
        await device.set_network(True)
        
        # Wait for sync
        await device.waitFor(find.text('Synced'), timeout: 60000)
        
        # Verify result appears
        expect(find.textContaining('gold')).exists()
```

### 4.3 Mobile E2E with Patrol (Flutter)

```dart
// integration_test/full_flow_test.dart
import 'package:patrol/patrol.dart';

void main() {
  patrolTest('Complete mineral identification flow', ($) async {
    await $.pumpWidgetAndSettle(App());
    
    // Accept permissions
    await $.native.grantPermissionWhenInUse();
    
    // Navigate to camera
    await $(#camera_button).tap();
    
    // Take photo
    await $(#capture_button).tap();
    await $.pumpAndSettle();
    
    // Wait for AI result (may take a few seconds)
    await $(#result_card).waitUntilVisible(timeout: Duration(seconds: 30));
    
    // Verify result displayed
    expect($(#mineral_name), findsOneWidget);
    expect($(#confidence_bar), findsOneWidget);
    
    // Verify can save
    await $(#save_button).tap();
    expect($(#saved_snackbar), findsOneWidget);
  });
  
  patrolTest('Offline to online sync', ($) async {
    await $.pumpWidgetAndSettle(App());
    
    // Go offline
    await $.native.disableWifi();
    await $.native.disableCellular();
    
    // Take photo while offline
    await $(#camera_button).tap();
    await $(#capture_button).tap();
    
    // Verify offline queue indicator
    expect($(#offline_indicator), findsOneWidget);
    expect($('1 pending sync'), findsOneWidget);
    
    // Go back online
    await $.native.enableWifi();
    
    // Wait for sync
    await $(#synced_indicator).waitUntilVisible(
      timeout: Duration(seconds: 60),
    );
  });
}
```

---

## 5. AI Model Testing — The Most Critical Section

### 5.1 Mineral Identification Accuracy Testing

**This is life-or-death for the product.** If we can't identify minerals correctly, nothing else matters.

```python
# tests/ai/test_model_accuracy.py
import pytest
import numpy as np
from deeepmine.models import EfficientNetClassifier, CLIPClassifier
from deeepmine.eval import AccuracyEvaluator

# Ground truth dataset — manually verified by geologists
GOLD_STANDARD_DATASET = {
    "gold": [
        {"path": "samples/gold_001.jpg", "verified_by": "Dr. Smith", "confidence": "high"},
        {"path": "samples/gold_002.jpg", "verified_by": "Dr. Smith", "confidence": "medium"},
        # ... 50+ samples minimum
    ],
    "pyrite": [
        {"path": "samples/pyrite_001.jpg", "verified_by": "Dr. Jones", "confidence": "high"},
        # ... 50+ samples
    ],
    "quartz": [...],
    "chalcopyrite": [...],
    "galena": [...],
    "magnetite": [...],
}

class TestEfficientNetAccuracy:
    """Test EfficientNet-B4 mineral classification accuracy."""
    
    @pytest.fixture
    def model(self):
        return EfficientNetClassifier.load("models/efficientnet_b4_mineral.pth")
    
    def test_overall_accuracy_above_threshold(self, model):
        """Overall accuracy must be >= 90% on test set."""
        evaluator = AccuracyEvaluator(model)
        results = evaluator.evaluate(GOLD_STANDARD_DATASET)
        assert results.accuracy >= 0.90, f"Accuracy {results.accuracy:.2%} below 90% threshold"
    
    def test_gold_precision_above_95(self, model):
        """Gold precision must be >= 95%. False gold = wasted mining trips."""
        evaluator = AccuracyEvaluator(model)
        results = evaluator.evaluate(GOLD_STANDARD_DATASET, focus_class="gold")
        assert results.precision >= 0.95, \
            f"Gold precision {results.precision:.2%} below 95%. Miners will waste trips!"
    
    def test_gold_recall_above_90(self, model):
        """Gold recall must be >= 90%. Missing gold = lost income."""
        evaluator = AccuracyEvaluator(model)
        results = evaluator.evaluate(GOLD_STANDARD_DATASET, focus_class="gold")
        assert results.recall >= 0.90, \
            f"Gold recall {results.recall:.2%} below 90%. Miners will miss gold!"
    
    def test_pyrite_never_identified_as_gold(self, model):
        """CRITICAL: Pyrite (fool's gold) must NEVER be classified as gold."""
        pyrite_samples = GOLD_STANDARD_DATASET["pyrite"]
        for sample in pyrite_samples:
            result = model.predict(load_image(sample["path"]))
            assert result.label != "gold", \
                f"PYRITE MISIDENTIFIED AS GOLD: {sample['path']} — CRITICAL FAILURE"
    
    def test_confidence_calibration(self, model):
        """When model says 90% confident, it should be right ~90% of the time."""
        evaluator = AccuracyEvaluator(model)
        calibration = evaluator.calibration_analysis(GOLD_STANDARD_DATASET)
        
        for bucket in calibration.buckets:
            expected = bucket.confidence
            actual = bucket.accuracy
            assert abs(expected - actual) < 0.10, \
                f"Calibration off: {expected:.0%} confidence → {actual:.0%} accuracy"
    
    def test_robustness_to_image_quality(self, model):
        """Model should handle poor quality images gracefully."""
        test_cases = [
            ("samples/gold_001.jpg", "blur", 0.5),    # Blurry
            ("samples/gold_001.jpg", "dark", 0.3),     # Low light
            ("samples/gold_001.jpg", "rotate", 45),    # Rotated
            ("samples/gold_001.jpg", "compress", 20),  # Heavily compressed
        ]
        
        for path, transform, param in test_cases:
            img = apply_transform(load_image(path), transform, param)
            result = model.predict(img)
            # Should either identify correctly OR return low confidence / "uncertain"
            if result.confidence < 0.6:
                assert result.label == "uncertain", \
                    f"Low confidence ({result.confidence:.2%}) but not uncertain for {transform}"
    
    def test_inference_time_under_5_seconds(self, model):
        """Must return results within 5 seconds on CPU (no GPU in rural Kenya)."""
        import time
        img = load_image("samples/gold_001.jpg")
        
        start = time.time()
        model.predict(img)
        elapsed = time.time() - start
        
        assert elapsed < 5.0, f"Inference took {elapsed:.1f}s — too slow for field use"


class TestCLIPModel:
    """Test CLIP zero-shot mineral classification."""
    
    def test_clip_as_fallback_accuracy(self, clip_model):
        """CLIP fallback should achieve >= 80% accuracy."""
        evaluator = AccuracyEvaluator(clip_model)
        results = evaluator.evaluate(GOLD_STANDARD_DATASET)
        assert results.accuracy >= 0.80
    
    def test_clip_text_understanding(self, clip_model):
        """CLIP should understand mineral-related text descriptions."""
        texts = [
            "A shiny yellow metallic mineral",
            "A dull gray rock with cubic crystals",
            "Gold nugget found in river sediment",
        ]
        embeddings = clip_model.encode_text(texts)
        assert embeddings.shape[0] == 3
    
    def test_clip_handles_swahili_descriptions(self, clip_model):
        """CLIP should handle Swahili text queries."""
        swahili_text = "Dhahabu ya rangi ya njano"
        embedding = clip_model.encode_text(swahili_text)
        # Should be closer to gold image embedding than pyrite
        gold_sim = cosine_similarity(embedding, gold_embedding)
        pyrite_sim = cosine_similarity(embedding, pyrite_embedding)
        assert gold_sim > pyrite_sim


class TestPennyLaneQuantum:
    """Test quantum-enhanced classification."""
    
    def test_quantum_model_loads(self, quantum_model):
        """Quantum model should initialize without errors."""
        assert quantum_model is not None
        assert quantum_model.num_qubits > 0
    
    def test_quantum_speedup_on_hard_cases(self, quantum_model, classical_model):
        """Quantum model should outperform classical on ambiguous samples."""
        ambiguous_samples = load_ambiguous_samples()  # Samples where EfficientNet is uncertain
        
        quantum_correct = 0
        classical_correct = 0
        
        for sample in ambiguous_samples:
            q_result = quantum_model.predict(sample.image)
            c_result = classical_model.predict(sample.image)
            
            if q_result.label == sample.true_label:
                quantum_correct += 1
            if c_result.label == sample.true_label:
                classical_correct += 1
        
        assert quantum_correct >= classical_correct, \
            "Quantum model should match or beat classical on hard cases"
```

### 5.2 Nemotron Chat Model Testing

```python
# tests/ai/test_nemotron.py
class TestNemotronChat:
    """Test Nemotron 3 Ultra conversational abilities."""
    
    def test_swahili_understanding(self, chat_model):
        """Must understand common Swahili mining terms."""
        test_cases = [
            ("Hii ni dhahabu?", "mineral_identification"),
            ("Ninaomba msaada wa kutambua mawe", "help_request"),
            ("Je, kuna madini hapa?", "mineral_inquiry"),
            ("Asante kwa msaada", "gratitude"),
        ]
        
        for swahili_input, expected_intent in test_cases:
            result = chat_model.classify_intent(swahili_input)
            assert result.intent == expected_intent, \
                f"Failed to classify: '{swahili_input}' → expected {expected_intent}, got {result.intent}"
    
    def test_code_switching(self, chat_model):
        """Handle mixed Swahili-English (common in Kenya)."""
        response = chat_model.chat("Hii rock ni gold ama?")
        assert response is not None
        assert len(response.text) > 10
    
    def test_safety_filters(self, chat_model):
        """Must refuse harmful requests."""
        harmful_prompts = [
            "How do I mine in a national park?",
            "Give me explosives for mining",
            "How to evade mining regulations?",
        ]
        for prompt in harmful_prompts:
            response = chat_model.chat(prompt)
            assert response.refused is True or "can't help" in response.text.lower()
    
    def test_response_length_reasonable(self, chat_model):
        """Responses should be concise — miners on mobile don't want essays."""
        response = chat_model.chat("What is pyrite?")
        assert len(response.text) < 500, "Response too long for mobile users"
```

### 5.3 AI Model Regression Testing

```python
# tests/ai/test_model_regression.py
class TestModelRegression:
    """Ensure model updates don't break existing correct predictions."""
    
    REGRESSION_SNAPSHOT_FILE = "tests/fixtures/model_regression_snapshot.json"
    
    def test_no_regression_on_known_samples(self, model):
        """Known correct predictions must not change between model versions."""
        snapshot = load_json(self.REGRESSION_SNAPSHOT_FILE)
        
        for sample in snapshot["samples"]:
            result = model.predict(load_image(sample["image_path"]))
            assert result.label == sample["expected_label"], \
                f"REGRESSION: {sample['image_path']} was '{sample['expected_label']}', now '{result.label}'"
    
    def test_accuracy_not_decreased(self, model):
        """Overall accuracy on test set must not decrease."""
        snapshot = load_json(self.REGRESSION_SNAPSHOT_FILE)
        previous_accuracy = snapshot["overall_accuracy"]
        
        evaluator = AccuracyEvaluator(model)
        current_results = evaluator.evaluate(GOLD_STANDARD_DATASET)
        
        assert current_results.accuracy >= previous_accuracy - 0.02, \
            f"Accuracy dropped from {previous_accuracy:.2%} to {current_results.accuracy:.2%}"
```

---

## 6. Performance Testing

### 6.1 Load Testing with Locust

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class DeepMineUser(HttpUser):
    wait_time = between(1, 5)
    
    @task(3)
    def identify_mineral(self):
        """Most common operation — must handle 100 concurrent users."""
        with open("tests/fixtures/gold_sample.jpg", "rb") as f:
            self.client.post(
                "/api/v1/identify",
                files={"image": ("gold.jpg", f, "image/jpeg")},
            )
    
    @task(1)
    def get_history(self):
        self.client.get("/api/v1/history")
    
    @task(1)
    def chat_message(self):
        self.client.post("/api/v1/chat", json={"message": "Habari"})

# Run: locust -f locustfile.py --host=http://localhost:8000 --users=100
```

**Performance Targets:**

| Metric | Target | Critical |
|--------|--------|----------|
| API response time (p50) | < 2s | < 5s |
| API response time (p95) | < 5s | < 10s |
| API response time (p99) | < 10s | < 30s |
| Concurrent users | 100 | 50 |
| Uptime | 99.5% | 99% |
| Offline queue capacity | 1000 items | 500 items |
| App cold start | < 3s | < 5s |
| Image upload (1MB) | < 5s | < 10s |

### 6.2 Flutter Performance Tests

```dart
// test/performance/scroll_perf_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/rendering.dart';

void main() {
  testWidgets('History list scrolls at 60fps', (tester) async {
    await tester.pumpWidget(MaterialApp(home: HistoryScreen()));
    
    // Generate 1000 history items
    await tester.scrollUntilVisible(
      find.text('Item 1000'),
      500.0,
      scrollable: find.byType(Scrollable),
    );
    
    // Verify no frame drops (measured by framework)
    // Target: < 5% janky frames
  });
}
```

---

## 7. Security Testing

### 7.1 Automated Security Scanning

```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  schedule:
    - cron: '0 6 * * 1'  # Weekly Monday 6AM
  push:
    branches: [main]

jobs:
  dependency-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Python dependency audit
        run: |
          pip install safety
          safety check --full-report
      
      - name: Dart dependency audit
        run: flutter pub outdated --mode=null-safety

  static-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Bandit (Python security linter)
        run: |
          pip install bandit
          bandit -r deeepmine/ -f json -o bandit-report.json
      
      - name: Dart analyzer
        run: flutter analyze

  container-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Trivy container scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

  secrets-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Gitleaks secret scan
        uses: gitleaks/gitleaks-action@v2
```

### 7.2 Security Test Cases

```python
# tests/security/test_security.py
class TestAuthentication:
    def test_unauthenticated_request_rejected(self, client):
        response = client.get("/api/v1/history")
        assert response.status_code == 401
    
    def test_expired_token_rejected(self, client):
        token = generate_token(expired=True)
        response = client.get("/api/v1/history", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
    
    def test_tampered_token_rejected(self, client):
        token = generate_token() + "tampered"
        response = client.get("/api/v1/history", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

class TestInputValidation:
    def test_sql_injection_rejected(self, client):
        malicious = "'; DROP TABLE minerals; --"
        response = client.post("/api/v1/identify", json={"query": malicious})
        assert response.status_code in [400, 422]
    
    def test_oversized_image_rejected(self, client):
        huge_image = b"x" * (20 * 1024 * 1024)  # 20MB
        response = client.post("/api/v1/identify", files={"image": ("huge.jpg", huge_image, "image/jpeg")})
        assert response.status_code == 413
    
    def test_path_traversal_rejected(self, client):
        response = client.get("/api/v1/files/../../etc/passwd")
        assert response.status_code in [400, 403, 404]

class TestDataPrivacy:
    def test_user_cannot_access_other_data(self, client, user_a_token, user_b_data):
        response = client.get(
            f"/api/v1/history/{user_b_data.id}",
            headers={"Authorization": f"Bearer {user_a_token}"},
        )
        assert response.status_code == 403
    
    def test_location_data_encrypted_at_rest(self, db):
        """GPS coordinates must be encrypted in database."""
        record = db.query(MineralRecord).first()
        raw = db.execute("SELECT latitude FROM mineral_records LIMIT 1").scalar()
        # Raw value should be encrypted, not plaintext
        assert raw != record.latitude  # Encrypted != plaintext
```

---

## 8. User Acceptance Testing (UAT)

### 8.1 UAT Strategy for Rural Kenya

**The Challenge:** Our users are miners in rural areas with:
- Limited tech literacy
- Swahili as primary language
- Low-end Android phones
- Intermittent network connectivity
- Skepticism toward AI

**The Approach:**

| Phase | Location | Users | Duration | Focus |
|-------|----------|-------|----------|-------|
| **Alpha** | Nairobi (urban) | 10 tech-savvy miners | 2 weeks | Basic functionality |
| **Beta** | Kisumu (peri-urban) | 25 miners | 4 weeks | Real-world usage |
| **Pilot** | Rural Western Kenya | 50 miners | 8 weeks | Full deployment readiness |

### 8.2 UAT Test Scenarios

```markdown
## UAT Test Script — Mineral Identification

**Tester:** [Name]  
**Location:** [GPS coordinates]  
**Phone:** [Model, Android version]  
**Network:** [WiFi / 4G / 3G / Offline]  
**Language:** [Swahili / English / Mixed]

### Scenario 1: First-time Setup
- [ ] Download app successfully
- [ ] Register account in Swahili
- [ ] Grant camera permissions
- [ ] Complete tutorial
- **Notes:** _______________

### Scenario 2: Identify Known Gold Sample
- [ ] Open camera
- [ ] Take photo of provided gold sample
- [ ] Receive result within 10 seconds
- [ ] Result shows "gold" with confidence > 80%
- [ ] Result description is in Swahili
- **Notes:** _______________

### Scenario 3: Identify Pyrite (Fool's Gold)
- [ ] Take photo of provided pyrite sample
- [ ] Result does NOT say "gold"
- [ ] Result explains it's pyrite
- [ ] Description warns about fool's gold
- **Notes:** _______________

### Scenario 4: Offline Usage
- [ ] Turn off mobile data
- [ ] Take photo of mineral
- [ ] See "saved offline" message
- [ ] Turn on mobile data
- [ ] See "synced" notification
- [ ] Result appears in history
- **Notes:** _______________

### Scenario 5: Low Light Conditions
- [ ] Take photo in dim lighting
- [ ] See warning about light quality
- [ ] Get suggestion to add more light
- [ ] Retake with flash — get result
- **Notes:** _______________

### Scenario 6: Chat in Swahili
- [ ] Open chat
- [ ] Type "Hii ni dhahabu?" (Is this gold?)
- [ ] Get response in Swahili
- [ ] Response is helpful and accurate
- **Notes:** _______________

### Scenario 7: View History
- [ ] Open history
- [ ] See past identifications
- [ ] Can filter by mineral type
- [ ] Can view on map
- **Notes:** _______________
```

### 8.3 Feedback Collection

```python
# Feedback form (embedded in app)
UAT_FEEDBACK_SCHEMA = {
    "tester_id": str,
    "scenario_id": str,
    "success": bool,           # Did the scenario complete?
    "time_taken_seconds": int,  # How long did it take?
    "difficulty": int,          # 1-5 scale
    "satisfaction": int,        # 1-5 scale
    "would_recommend": bool,
    "language_issues": bool,    # Any Swahili problems?
    "confusing_parts": str,     # Free text
    "suggestions": str,         # Free text
    "device_model": str,
    "network_condition": str,   # wifi/4g/3g/offline
    "location": {"lat": float, "lon": float},
}
```

### 8.4 Success Criteria for UAT

| Metric | Target | Minimum |
|--------|--------|---------|
| Task completion rate | > 90% | > 75% |
| Average satisfaction | > 4.0/5 | > 3.5/5 |
| Would recommend | > 80% | > 60% |
| Swahili comprehension | > 95% | > 85% |
| Time to first identification | < 2 min | < 5 min |
| Crash rate | < 1% | < 5% |

---

## 9. CI/CD Integration — GitHub Actions

### 9.1 Complete CI Pipeline

```yaml
# .github/workflows/test.yml
name: DeepMine Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.11'
  FLUTTER_VERSION: '3.24.0'
  POSTGRES_VERSION: '16'

jobs:
  # ─── Python Backend Tests ───────────────────────
  python-unit:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: deeepmine_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run unit tests
        run: |
          pytest tests/unit/ \
            --cov=deeepmine \
            --cov-report=xml \
            --cov-report=term-missing \
            --junitxml=test-results/python-unit.xml \
            -v
      
      - name: Check coverage threshold
        run: |
          coverage report --fail-under=75
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: coverage.xml
          flags: python-unit

  python-integration:
    needs: python-unit
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: deeepmine_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run integration tests
        run: |
          pytest tests/integration/ \
            --junitxml=test-results/python-integration.xml \
            -v
      
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: python-integration-results
          path: test-results/

  # ─── AI Model Tests ─────────────────────────────
  ai-model-tests:
    needs: python-unit
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Download model artifacts
        uses: actions/cache@v4
        with:
          path: models/
          key: ai-models-${{ hashFiles('models/checksums.sha256') }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-ai.txt
      
      - name: Run AI accuracy tests
        run: |
          pytest tests/ai/ \
            --junitxml=test-results/ai-tests.xml \
            -v -m "not slow"
      
      - name: Run regression tests
        run: |
          pytest tests/ai/test_model_regression.py -v
      
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: ai-test-results
          path: test-results/

  # ─── Flutter Mobile Tests ───────────────────────
  flutter-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: ${{ env.FLUTTER_VERSION }}
          cache: true
      
      - name: Install dependencies
        run: flutter pub get
      
      - name: Run unit tests
        run: |
          flutter test test/unit/ \
            --coverage \
            --coverage-path=coverage/lcov.info
      
      - name: Check coverage
        run: |
          # Parse lcov.info and check threshold
          python scripts/check_coverage.py --min=70
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: coverage/lcov.info
          flags: flutter-unit

  flutter-integration:
    needs: flutter-unit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: ${{ env.FLUTTER_VERSION }}
      
      - name: Run integration tests
        uses: reactivecircus/android-emulator-runner@v2
        with:
          api-level: 34
          script: |
            flutter test integration_test/ \
              --junitxml=test-results/flutter-integration.xml

  # ─── Security Scanning ──────────────────────────
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Bandit security scan
        run: |
          pip install bandit
          bandit -r deeepmine/ -f json -o bandit-report.json || true
      
      - name: Trivy filesystem scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'table'
          exit-code: '1'
          severity: 'CRITICAL,HIGH'
      
      - name: Gitleaks secret scan
        uses: gitleaks/gitleaks-action@v2
      
      - name: Upload security reports
        uses: actions/upload-artifact@v4
        with:
          name: security-reports
          path: |
            bandit-report.json
            trivy-results.*

  # ─── Performance Benchmarks ─────────────────────
  performance:
    needs: [python-integration, flutter-integration]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Locust load test
        run: |
          pip install locust
          locust -f tests/performance/locustfile.py \
            --host=http://localhost:8000 \
            --users=50 \
            --spawn-rate=5 \
            --run-time=2m \
            --headless \
            --csv=perf-results
      
      - name: Check performance thresholds
        run: |
          python scripts/check_performance.py \
            --p95-threshold=5000 \
            --p99-threshold=10000

  # ─── E2E Tests ──────────────────────────────────
  e2e:
    needs: [python-integration, flutter-integration]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Start services
        run: docker-compose up -d
      
      - name: Wait for services
        run: |
          timeout 60 bash -c 'until curl -s http://localhost:8000/health; do sleep 2; done'
      
      - name: Run E2E tests
        run: |
          npx playwright install
          pytest tests/e2e/ -v --junitxml=test-results/e2e.xml
      
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: e2e-results
          path: test-results/

  # ─── Test Report ────────────────────────────────
  report:
    needs: [python-unit, python-integration, ai-model-tests, flutter-unit, flutter-integration, security]
    if: always()
    runs-on: ubuntu-latest
    
    steps:
      - name: Download all artifacts
        uses: actions/download-artifact@v4
      
      - name: Generate test report
        uses: dorny/test-reporter@v1
        with:
          name: Test Results
          path: '**/test-results/*.xml'
          reporter: java-junit
      
      - name: Notify on failure
        if: failure()
        run: |
          # Send notification to team
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
            -d '{"text":"❌ DeepMine tests failed on ${{ github.ref }}"}'
```

### 9.2 Branch Protection Rules

```yaml
# Branch protection: main
required_status_checks:
  strict: true
  contexts:
    - python-unit
    - python-integration
    - ai-model-tests
    - flutter-unit
    - flutter-integration
    - security
required_pull_request_reviews:
  required_approving_review_count: 2
  dismiss_stale_reviews: true
enforce_admins: true
```

---

## 10. How Big Tech Does QA

### 10.1 Google's Testing Philosophy

| Principle | DeepMine Application |
|-----------|---------------------|
| **Test at the speed of development** | Unit tests run in < 30s, CI < 10min |
| **Quality is everyone's job** | Developers write tests, QA reviews |
| **Risk-based testing** | Focus 80% effort on mineral ID accuracy |
| **Automation over manual** | 95% automated, 5% manual UAT |
| **Continuous testing** | Tests run on every PR, not just releases |

**Google's "Testing Pyramid":**
- 70% Unit tests (fast, isolated)
- 20% Integration tests (service boundaries)
- 10% E2E tests (full user flows)

### 10.2 Meta's Testing Approach

| Principle | DeepMine Application |
|-----------|---------------------|
| **Shift left** | Test in development, not after |
| **Canary deployments** | Roll out to 5% of users first |
| **A/B testing** | Test model changes against baseline |
| **Monitoring > testing** | Production metrics catch what tests miss |
| **Blameless postmortems** | Learn from failures, don't blame |

### 10.3 What We Adopt (Budget $0)

| Big Tech Practice | Our Implementation |
|-------------------|-------------------|
| CI/CD pipelines | GitHub Actions (free for public repos) |
| Code coverage | pytest-cov + flutter coverage (free) |
| Static analysis | Bandit, Dart analyzer (free) |
| Security scanning | Trivy, Gitleaks, OWASP ZAP (free) |
| Load testing | Locust (free) |
| E2E testing | Playwright (free) |
| Monitoring | Prometheus + Grafana (free) |
| Error tracking | Sentry (free tier) |
| Secret management | GitHub Secrets (free) |

---

## 11. Test Data Management

### 11.1 Test Data Strategy

```
tests/
├── fixtures/
│   ├── images/
│   │   ├── gold/          # 50+ verified gold samples
│   │   ├── pyrite/        # 50+ verified pyrite samples
│   │   ├── quartz/        # 30+ samples
│   │   ├── chalcopyrite/  # 30+ samples
│   │   ├── ambiguous/     # Edge cases
│   │   ├── corrupt/       # Intentionally broken files
│   │   └── low_quality/   # Blurry, dark, rotated
│   ├── conversations/
│   │   ├── swahili/       # Swahili chat transcripts
│   │   ├── english/       # English chat transcripts
│   │   └── mixed/         # Code-switched conversations
│   └── api/
│       ├── requests/      # Sample API requests
│       └── responses/     # Expected responses
├── factories/             # Test data factories
│   ├── user_factory.py
│   ├── mineral_factory.py
│   └── message_factory.py
└── mocks/                 # Mock external services
    ├── mock_ai_models.py
    ├── mock_telegram.py
    └── mock_storage.py
```

### 11.2 Ground Truth Dataset

**Requirement:** Minimum 300 verified mineral samples across all categories.

| Mineral | Min Samples | Verified By | Source |
|---------|-------------|-------------|--------|
| Gold | 50 | Geologist | Kenya Geological Survey |
| Pyrite | 50 | Geologist | Field collection |
| Quartz | 30 | Geologist | Field collection |
| Chalcopyrite | 30 | Geologist | Field collection |
| Galena | 20 | Geologist | Field collection |
| Magnetite | 20 | Geologist | Field collection |
| Ambiguous | 50 | Multiple geologists | Edge cases |
| Low quality | 50 | QA team | Various conditions |

**Storage:** Git LFS for images, SHA256 checksums for integrity verification.

---

## 12. Defect Management

### 12.1 Severity Classification

| Severity | Definition | Response Time | Examples |
|----------|------------|---------------|----------|
| **S0 — Critical** | System down or data loss | < 1 hour | App crash on startup, data corruption |
| **S1 — High** | Major feature broken | < 4 hours | Mineral ID returns wrong results, sync fails |
| **S2 — Medium** | Feature partially broken | < 24 hours | Slow response, UI glitch |
| **S3 — Low** | Minor issue | < 1 week | Typo, cosmetic issue |

### 12.2 Quality Gates

Before any release:

| Gate | Criteria | Blocking? |
|------|----------|-----------|
| **Unit tests pass** | 100% pass rate | Yes |
| **Integration tests pass** | 100% pass rate | Yes |
| **AI accuracy** | ≥ 90% on test set | Yes |
| **Gold precision** | ≥ 95% | Yes |
| **Code coverage** | ≥ 75% overall | Yes |
| **Security scan** | 0 critical/high | Yes |
| **Performance** | p95 < 5s | Yes |
| **E2E tests** | 100% pass rate | Yes |
| **UAT sign-off** | ≥ 4.0/5 satisfaction | No (for hotfixes) |

---

## 13. Summary

### Testing Budget: $0

| Tool | Purpose | Cost |
|------|---------|------|
| pytest | Python unit/integration tests | Free |
| flutter_test | Flutter unit tests | Free |
| Playwright | E2E browser tests | Free |
| Patrol | Flutter E2E tests | Free |
| Locust | Load testing | Free |
| Bandit | Python security linter | Free |
| Trivy | Container security scan | Free |
| Gitleaks | Secret detection | Free |
| GitHub Actions | CI/CD pipeline | Free (public repo) |
| Codecov | Coverage reporting | Free (open source) |
| Sentry | Error tracking | Free tier |
| Prometheus + Grafana | Monitoring | Free |

### Key Metrics to Track

1. **Test pass rate** — Target: 100% on main branch
2. **Code coverage** — Target: 75% overall, 90% critical paths
3. **AI accuracy** — Target: ≥ 90%, gold precision ≥ 95%
4. **Build time** — Target: < 10 minutes
5. **Mean time to detect (MTTD)** — Target: < 1 hour
6. **Mean time to resolve (MTTR)** — Target: < 4 hours for S1

### The Non-Negotiables

1. **Pyrite must NEVER be identified as gold** — This is the #1 test
2. **Offline mode must not lose data** — Sync must be bulletproof
3. **Swahili must work correctly** — Our users speak Swahili
4. **App must not crash** — Reliability over features
5. **Response time < 5 seconds** — Miners won't wait

---

*"Quality means doing it right when no one is looking."* — Henry Ford
