/* 
Script to clear out the ADL LRS
This script will remove all entries of xAPI data, leaving the Agents intact.
Those can be removed with another script.
*/
\echo "Clearing Statement Context objects ..."
DELETE FROM lrs_statement_context_ca_parent;
DELETE FROM lrs_statement_context_ca_category;
DELETE FROM lrs_statement_context_ca_grouping;
DELETE FROM lrs_statement_context_ca_other;

\echo "Clearing Sub-Statement objects ..."
DELETE FROM lrs_substatement_context_ca_parent;
DELETE FROM lrs_substatement_context_ca_category;
DELETE FROM lrs_substatement_context_ca_grouping;
DELETE FROM lrs_substatement_context_ca_other;
DELETE FROM lrs_substatement;

\echo "Clearing Statement Attachment objects ..."
DELETE FROM lrs_statementattachment;

\echo "Clearing Statements ..."
DELETE FROM lrs_statement;

\echo "Clearing xAPI components ..."
DELETE FROM lrs_verb;

DELETE FROM lrs_activitystate;
DELETE FROM lrs_activityprofile;

\echo "Clearing OAuth cache ..."
DELETE FROM oauth_provider_nonce;
DELETE FROM oauth_provider_consumer;
DELETE FROM oauth_provider_token;

\echo "Clearing Activities ..."
DELETE FROM lrs_activity;

\echo "Clearing hooks ..."
DELETE FROM adl_lrs_hook;
