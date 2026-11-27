"""Required concrete unittest groups, independent of the loader's returned suite."""

PORTABLE_GROUPS = frozenset("""
test_package.Package test_standard_alignment.StandardAlignment test_reader_platform.ReaderPlatformTests
test_a1_matrix_regressions.ReaderFailures test_a1_matrix_regressions.ArtifactIdentity
test_emission_result.ResultTransport test_protocol.Protocol test_env_literal.Grammar
test_r2_confidentiality.EmissionModule test_f3_ambiguous.AmbiguousCollection
test_platform_evidence.PlatformEvidence test_platform_render.RendererPlatform
test_platform_render.PreapprovalTools test_confidential_names.NameMapPortable
test_enrolled_isolation.EnrollmentIsolation test_recovery_review.RecoveryReview
test_scratch_retention.ScratchRetention test_secret_scalars.DecodedBooleans test_render_map.MapPortable
test_round3_state.TreeInventory test_validation_prerequisites.ValidationContracts
test_review_protocol.ReviewProtocol test_workflow_decisions.Decisions test_validation_scope.ValidationScope
""".split())

NATIVE_GROUPS = PORTABLE_GROUPS | frozenset("""
test_masking_proof.MaskingProof test_reader_reported_errors.ReaderReportedErrors
test_emission_corrective.CorrectiveEmission test_a2_corrective.RunnerCorrective
test_a1_boundary_regressions.BoundaryRegressions test_confidential_names.ConfidentialNames
test_check_registry.CheckRegistry test_cli_boundary.CliBoundaries test_final_review_r1.FinalReviewR1
test_f3_ambiguous.AmbiguousRefusal test_evidence_stage1.Stage1 test_evidence.Evidence
test_evidence_destination.EvidenceDestination test_round3_state.NativeState test_childenv.Childenv
test_inspection_git.InspectionGit test_checkpoint.Contract test_nested.Nested
test_env_literal.EndToEnd test_round2_recovery.RecoveryRound2 test_restore_labels.RestoreLabels
test_evidence_readings.Readings test_final_review_r2.RunnerIdentity test_final_review_r2.Emission
test_final_review_r2.RecordedPaths test_final_review_r2.WrapperStatus test_evidence_node.NodeLoaders
test_r2_status.StatusMatrix test_render_pdf.Renderer test_render_pdf.RendererOutputSafety
test_literal_matrix.DifferentialMatrix test_r2_emission_corrective.CorrectiveCLI
test_planstate.PlanPublication test_watched.Watched test_render_map.MapRenderer
test_r2_confidentiality.ConfidentialityBattery test_tree.Tree test_stage1_acceptance.Acceptance
""".split())


def method_ids(suite):
    import unittest
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from method_ids(test)
        else:
            yield test.id()


def discovery(scope, suite):
    ids = list(method_ids(suite))
    groups = {method.rsplit(".", 1)[0] for method in ids}
    required = PORTABLE_GROUPS if scope == "portable" else NATIVE_GROUPS
    missing = sorted(required - groups)
    duplicates = len(ids) - len(set(ids))
    return {"methods": len(ids), "required_groups": len(required), "missing_groups": missing,
            "duplicate_methods": duplicates, "complete": bool(ids) and not missing and not duplicates}
