"""Tests for `ai/fall_detection/preprocess.py`.

These are split into two groups:

* **Pure tests** that need no dataset and no model. They run everywhere, and
  they pin down the parsing rules, the unit conversion, the split behaviour and
  the train-only scaler rule.
* **Dataset tests** that are skipped when the (git-ignored) SisFall archive is
  not present. They check the module against the real files.

The pure tests matter most: they are what keeps a future edit from silently
introducing the two mistakes that would invalidate every reported number — a
row-wise split, or a scaler fitted on the test set.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

from ai.fall_detection import preprocess as pp

ARCHIVE = (
    pathlib.Path(__file__).resolve().parents[2] / "data" / "raw" / "SisFall_dataset.zip"
)
needs_archive = pytest.mark.skipif(
    not ARCHIVE.exists(),
    reason="SisFall archive not downloaded (see docs/datasets/sisfall.md)",
)


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------


def test_adc_conversion_matches_the_readme_formula() -> None:
    """g = (2 * Range) / 2**Resolution * AD, with Range=16 and Resolution=13."""
    expected = (2 * 16) / (2**13)
    assert pp.ADXL345_G_PER_ADC_BIT == pytest.approx(expected)
    # 8192 counts is 2**13, i.e. exactly the full +/- range in one direction.
    assert pp.counts_to_g(np.array([8192.0]))[0] == pytest.approx(32.0)
    assert pp.counts_to_g(np.array([0.0]))[0] == 0.0


def test_conversion_does_not_mutate_its_input() -> None:
    counts = np.array([100.0, -100.0])
    original = counts.copy()
    pp.counts_to_g(counts)
    assert np.array_equal(counts, original)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def test_parse_handles_padding_crlf_and_trailing_semicolon() -> None:
    """Exactly the shape the real files use: CRLF, padded ints, trailing ';'."""
    text = "  17,-179, -99, -18,-504,-352,  76,-697,-279;\r\n" "  15,-174, -90, -53,-568,-306,  48,-675,-254;\r\n"
    parsed = pp.parse_recording(text)

    assert parsed.shape == (2, 3)
    # First three columns are ADXL345, converted to g.
    assert parsed[0, 0] == pytest.approx(17 * pp.ADXL345_G_PER_ADC_BIT)
    assert parsed[0, 1] == pytest.approx(-179 * pp.ADXL345_G_PER_ADC_BIT)
    assert parsed[1, 2] == pytest.approx(-90 * pp.ADXL345_G_PER_ADC_BIT)


def test_parse_skips_malformed_rows_rather_than_guessing() -> None:
    """A wrong field count must be dropped, not coerced into a fake spike."""
    text = (
        "1,2,3,4,5,6,7,8,9;\n"
        "1,2,3;\n"  # too few fields
        "1,2,3,4,5,6,7,8,9,10;\n"  # too many
        "a,b,c,d,e,f,g,h,i;\n"  # not integers
        "\n"  # blank
        "2,2,3,4,5,6,7,8,9;\n"
    )
    parsed = pp.parse_recording(text)

    assert parsed.shape == (2, 3)
    assert parsed[1, 0] == pytest.approx(2 * pp.ADXL345_G_PER_ADC_BIT)


def test_parse_of_empty_text_yields_an_empty_array() -> None:
    parsed = pp.parse_recording("")
    assert parsed.shape == (0, 3)


# ---------------------------------------------------------------------------
# Filenames and subjects
# ---------------------------------------------------------------------------


def test_subject_and_cohort_are_read_from_the_filename() -> None:
    assert pp.subject_of("D01_SA01_R01.txt") == ("SA01", "adult")
    assert pp.subject_of("F15_SE06_R05.txt") == ("SE06", "elderly")
    # A full archive path works too.
    assert pp.subject_of("SisFall_dataset/SE15/D17_SE15_R01.txt") == ("SE15", "elderly")


def test_an_unrecognised_filename_fails_loudly() -> None:
    """A mis-named file would silently corrupt the subject-wise split."""
    with pytest.raises(ValueError, match="does not match"):
        pp.subject_of("not_a_sisfall_file.txt")


# ---------------------------------------------------------------------------
# Windowing and features
# ---------------------------------------------------------------------------


def _recording(rows: int, label: int, value: float = 0.0) -> pp.Recording:
    return pp.Recording(
        code="D01" if label == 0 else "F01",
        subject="SA01",
        cohort="adult",
        run="01",
        label=label,
        accel_g=np.full((rows, 3), value, dtype=np.float64),
    )


def test_windowing_uses_a_fixed_length_and_stride() -> None:
    rec = _recording(rows=1000, label=0)
    windows = pp.build_windows(rec, window_rows=400, stride=200)

    # starts at 0, 200, 400, 600 -> the 800 start would need 1200 rows.
    assert [w.start_row for w in windows] == [0, 200, 400, 600]
    assert all(w.label == 0 for w in windows)
    assert all(w.subject == "SA01" for w in windows)


def test_a_recording_shorter_than_one_window_produces_nothing() -> None:
    assert pp.build_windows(_recording(rows=10, label=1), window_rows=400) == []


def test_windowing_rejects_a_stride_larger_than_the_window() -> None:
    """Otherwise windows would silently skip data."""
    with pytest.raises(ValueError, match="stride must not exceed"):
        pp.build_windows(_recording(rows=1000, label=0), window_rows=200, stride=400)


def test_a_resting_sensor_has_a_magnitude_near_one_g() -> None:
    """Gravity sanity check: with only z = 1 g, magnitude must be ~1 g."""
    samples = np.zeros((400, 3), dtype=np.float64)
    samples[:, 2] = 1.0
    features = pp.extract_features(samples)

    assert features["mag_mean"] == pytest.approx(1.0)
    assert features["mag_max"] == pytest.approx(1.0)
    assert features["mag_std"] == pytest.approx(0.0)
    assert features["x_std"] == pytest.approx(0.0)


def test_magnitude_is_invariant_to_which_axis_is_up() -> None:
    """The point of a magnitude feature: orientation must not change it."""
    on_z = np.zeros((400, 3), dtype=np.float64)
    on_z[:, 2] = 1.0
    on_x = np.zeros((400, 3), dtype=np.float64)
    on_x[:, 0] = 1.0

    assert pp.extract_features(on_z)["mag_mean"] == pytest.approx(
        pp.extract_features(on_x)["mag_mean"]
    )


def test_features_have_a_stable_documented_order() -> None:
    names = pp.feature_names()
    assert names == [f"{axis}_{suffix}" for axis in ("x", "y", "z", "mag")
                     for suffix in ("mean", "std", "min", "max", "median", "iqr",
                                    "rms", "range", "mean_abs_diff", "zero_crossings")]
    # Order is a contract: the model stores these names and serving must match.
    assert len(names) == len(set(names))


def test_extract_features_rejects_the_wrong_shape() -> None:
    with pytest.raises(ValueError, match="shape"):
        pp.extract_features(np.zeros((10, 2)))


def test_zero_crossings_counts_oscillation() -> None:
    """A square-ish alternating signal should cross the mean on every step."""
    alternating = np.zeros((400, 3), dtype=np.float64)
    alternating[::2, 2] = 1.0
    alternating[1::2, 2] = -1.0

    features = pp.extract_features(alternating)
    assert features["z_zero_crossings"] > 100


# ---------------------------------------------------------------------------
# Splitting — the property that keeps the evaluation honest
# ---------------------------------------------------------------------------


def test_split_never_puts_a_subject_in_both_sides() -> None:
    subjects = [f"SA{i:02d}" for i in range(1, 24)]
    train, test = pp.split_subjects(subjects, test_fraction=0.25, seed=1)

    assert set(train).isdisjoint(test)
    assert set(train) | set(test) == set(subjects)


def test_split_is_deterministic_for_a_given_seed() -> None:
    """A rerun must reproduce the reported numbers exactly."""
    subjects = [f"SA{i:02d}" for i in range(1, 24)]
    assert pp.split_subjects(subjects, seed=7) == pp.split_subjects(subjects, seed=7)


def test_a_different_seed_gives_a_different_split() -> None:
    subjects = [f"SA{i:02d}" for i in range(1, 24)]
    assert pp.split_subjects(subjects, seed=1) != pp.split_subjects(subjects, seed=2)


def test_split_always_leaves_at_least_one_subject_for_training() -> None:
    """Two subjects at 50 % must not produce an empty training set."""
    train, test = pp.split_subjects(["SA01", "SA02"], test_fraction=0.5, seed=0)
    assert train and test
    assert set(train).isdisjoint(test)


def test_split_rejects_a_degenerate_fraction() -> None:
    subjects = ["SA01", "SA02", "SA03"]
    with pytest.raises(ValueError, match="test_fraction"):
        pp.split_subjects(subjects, test_fraction=0.0)
    with pytest.raises(ValueError, match="test_fraction"):
        pp.split_subjects(subjects, test_fraction=1.0)


def test_split_of_an_empty_list_fails_loudly() -> None:
    with pytest.raises(ValueError, match="empty"):
        pp.split_subjects([])


# ---------------------------------------------------------------------------
# Scaling — must be fitted on training rows only
# ---------------------------------------------------------------------------


def test_scaler_standardises_the_training_rows() -> None:
    base = {name: 0.0 for name in pp.feature_names()}
    rows = []
    for i, value in enumerate((1.0, 3.0, 5.0)):
        row = dict(base)
        row["x_mean"] = value
        rows.append(row)
    scaler = pp.fit_scaler(rows)

    transformed = scaler.transform(pp.feature_matrix([_window_from(row) for row in rows]))
    # Mean 3, std ~1.633 -> the middle row maps to 0 on x_mean.
    assert transformed[1, pp.feature_names().index("x_mean")] == pytest.approx(0.0, abs=1e-9)


def _window_from(row: dict[str, float]) -> pp.Window:
    return pp.Window(
        subject="SA01", cohort="adult", code="D01", run="01", label=0,
        start_row=0, features=row,
    )


def test_a_constant_feature_does_not_divide_by_zero() -> None:
    rows = [{name: 7.0 for name in pp.feature_names()} for _ in range(2)]
    scaler = pp.fit_scaler(rows)
    transformed = scaler.transform(pp.feature_matrix([_window_from(rows[0])]))
    assert np.all(np.isfinite(transformed))


def test_a_partial_feature_dict_is_reported_clearly() -> None:
    """A missing feature must name itself, not surface as a bare KeyError."""
    with pytest.raises(ValueError, match="is missing from row"):
        pp.fit_scaler([{"x_mean": 1.0}])


def test_fitting_a_scaler_on_nothing_fails_loudly() -> None:
    with pytest.raises(ValueError, match="zero feature rows"):
        pp.fit_scaler([])


def test_feature_matrix_column_order_follows_feature_names() -> None:
    rec = _recording(rows=400, label=0, value=0.5)
    windows = pp.build_windows(rec)
    matrix = pp.feature_matrix(windows)

    assert matrix.shape == (len(windows), len(pp.feature_names()))
    # Value 0.5 everywhere -> every axis mean is 0.5 on all axes.
    names = pp.feature_names()
    for axis in ("x", "y", "z", "mag"):
        assert matrix[0, names.index(f"{axis}_mean")] == pytest.approx(
            0.5 if axis != "mag" else 0.5 * np.sqrt(3)
        )


# ---------------------------------------------------------------------------
# Against the real archive (skipped when it is absent)
# ---------------------------------------------------------------------------


@needs_archive
def test_real_archive_has_the_documented_cohorts() -> None:
    subjects = pp.all_subjects(ARCHIVE)
    assert len(subjects) == 38
    assert sum(1 for s in subjects if s.startswith("SA")) == 23
    assert pp.elderly_subjects(ARCHIVE) == [f"SE{i:02d}" for i in range(1, 16)]


@needs_archive
def test_only_one_elderly_subject_simulated_falls() -> None:
    """This single fact is why the elderly result must be labelled as one person."""
    elderly_with_falls = pp.subjects_with_falls(ARCHIVE) & set(pp.elderly_subjects(ARCHIVE))
    assert elderly_with_falls == {"SE06"}


@needs_archive
def test_a_real_fall_recording_looks_like_a_fall_and_an_adl_does_not() -> None:
    """Physics check against real data: a fall spikes well above 1 g."""
    fall = pp.read_recording_from_archive(ARCHIVE, "SisFall_dataset/SA01/F01_SA01_R01.txt")
    adl = pp.read_recording_from_archive(ARCHIVE, "SisFall_dataset/SA01/D01_SA01_R01.txt")

    assert fall is not None and adl is not None
    assert fall.label == 1 and adl.label == 0
    assert fall.duration_s == pytest.approx(15.0, abs=0.1)

    fall_peak = float(np.sqrt((fall.accel_g**2).sum(axis=1)).max())
    adl_mean = float(np.sqrt((adl.accel_g**2).sum(axis=1)).mean())

    assert fall_peak > 3.0, "a real fall should exceed 3 g"
    assert 0.5 < adl_mean < 1.5, "walking should sit near 1 g on average"


@needs_archive
def test_real_windows_carry_both_classes_and_expected_labels() -> None:
    fall = pp.read_recording_from_archive(ARCHIVE, "SisFall_dataset/SA01/F01_SA01_R01.txt")
    assert fall is not None
    windows = pp.build_windows(fall)

    assert len(windows) == 14
    assert {w.label for w in windows} == {1}
    assert {w.code for w in windows} == {"F01"}
