--
-- PostgreSQL database dump
--

-- Dumped from database version 10.10 (Debian 10.10-1.pgdg90+1)
-- Dumped by pg_dump version 10.10 (Debian 10.10-1.pgdg90+1)
--
-- Changes from the dump:
-- * Added "IF NOT EXISTS" everywhere
-- * Moved constraints into table definitions (in case EXISTS)
-- * Reordered tables (so constraints' dependent tables exist)


--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "plpgsql" WITH SCHEMA "pg_catalog";


--
-- Name: EXTENSION "plpgsql"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "plpgsql" IS 'PL/pgSQL procedural language';

--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."django_content_type" (
    "id" integer NOT NULL,
    "app_label" character varying(100) NOT NULL,
    "model" character varying(100) NOT NULL,
    CONSTRAINT "django_content_type_app_label_model_76bd3d3b_uniq" UNIQUE ("app_label", "model"),
    CONSTRAINT "django_content_type_pkey" PRIMARY KEY ("id")
);


--
-- Name: auth_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."auth_user" (
    "id" integer NOT NULL,
    "password" character varying(128) NOT NULL,
    "last_login" timestamp with time zone,
    "is_superuser" boolean NOT NULL,
    "username" character varying(150) NOT NULL,
    "first_name" character varying(150) NOT NULL,
    "last_name" character varying(150) NOT NULL,
    "email" character varying(254) NOT NULL,
    "is_staff" boolean NOT NULL,
    "is_active" boolean NOT NULL,
    "date_joined" timestamp with time zone NOT NULL,
    CONSTRAINT "auth_user_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "auth_user_username_key" UNIQUE ("username")
);


--
-- Name: workflow; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."workflow" (
    "id" integer NOT NULL,
    "name" character varying(200) NOT NULL,
    "creation_date" timestamp with time zone NOT NULL,
    "anonymous_owner_session_key" character varying(40),
    "original_workflow_id" integer,
    "public" boolean NOT NULL,
    "example" boolean NOT NULL,
    "in_all_users_workflow_lists" boolean NOT NULL,
    "lesson_slug" character varying(100),
    "selected_tab_position" integer NOT NULL,
    "last_delta_id" integer,
    "owner_id" integer,
    "last_viewed_at" timestamp with time zone NOT NULL,
    "has_custom_report" boolean NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    CONSTRAINT "server_workflow_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "server_workflow_owner_id_aa1f16c9_fk_auth_user_id" FOREIGN KEY ("owner_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: account_emailaddress; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."account_emailaddress" (
    "id" integer NOT NULL,
    "email" character varying(254) NOT NULL,
    "verified" boolean NOT NULL,
    "primary" boolean NOT NULL,
    "user_id" integer NOT NULL,
    CONSTRAINT "account_emailaddress_email_key" UNIQUE ("email"),
    CONSTRAINT "account_emailaddress_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "account_emailaddress_user_id_2c513194_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: product; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."product" (
    "id" integer NOT NULL,
    "stripe_product_id" character varying(50) NOT NULL,
    "stripe_product_name" "text" NOT NULL,
    "max_fetches_per_day" integer NOT NULL,
    "max_delta_age_in_days" integer NOT NULL,
    CONSTRAINT "product_pkey" PRIMARY KEY ("id")
);


--
-- Name: price; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."price" (
    "id" integer NOT NULL,
    "stripe_price_id" character varying(50) NOT NULL,
    "stripe_active" boolean NOT NULL,
    "stripe_amount" integer NOT NULL,
    "stripe_currency" character varying(3) NOT NULL,
    "product_id" integer NOT NULL,
    "stripe_interval" "text" NOT NULL,
    CONSTRAINT "plan_stripe_amount_check" CHECK (("stripe_amount" >= 0)),
    CONSTRAINT "plan_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "plan_stripe_price_id_key" UNIQUE ("stripe_price_id"),
    CONSTRAINT "price_product_id_4d9c683d_fk_product_id" FOREIGN KEY ("product_id") REFERENCES "public"."product"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: account_emailaddress_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."account_emailaddress_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: account_emailaddress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."account_emailaddress_id_seq" OWNED BY "public"."account_emailaddress"."id";


--
-- Name: account_emailconfirmation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."account_emailconfirmation" (
    "id" integer NOT NULL,
    "created" timestamp with time zone NOT NULL,
    "sent" timestamp with time zone,
    "key" character varying(64) NOT NULL,
    "email_address_id" integer NOT NULL,
    CONSTRAINT "account_emailconfirmation_key_key" UNIQUE ("key"),
    CONSTRAINT "account_emailconfirmation_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "account_emailconfirm_email_address_id_5b7f8c58_fk_account_e" FOREIGN KEY ("email_address_id") REFERENCES "public"."account_emailaddress"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: account_emailconfirmation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."account_emailconfirmation_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: account_emailconfirmation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."account_emailconfirmation_id_seq" OWNED BY "public"."account_emailconfirmation"."id";


--
-- Name: acl_entry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."acl_entry" (
    "id" integer NOT NULL,
    "email" character varying(254) NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "can_edit" boolean NOT NULL,
    "workflow_id" integer NOT NULL,
    CONSTRAINT "server_aclentry_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "server_aclentry_workflow_id_email_b8b0f3a8_uniq" UNIQUE ("workflow_id", "email"),
    CONSTRAINT "server_aclentry_workflow_id_c722e228_fk_server_workflow_id" FOREIGN KEY ("workflow_id") REFERENCES "public"."workflow"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."auth_group" (
    "id" integer NOT NULL,
    "name" character varying(150) NOT NULL,
    CONSTRAINT "auth_group_name_key" UNIQUE ("name"),
    CONSTRAINT "auth_group_pkey" PRIMARY KEY ("id")
);


--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."auth_group_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."auth_group_id_seq" OWNED BY "public"."auth_group"."id";

--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."auth_permission" (
    "id" integer NOT NULL,
    "name" character varying(255) NOT NULL,
    "content_type_id" integer NOT NULL,
    "codename" character varying(100) NOT NULL,
    CONSTRAINT "auth_permission_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "auth_permission_content_type_id_codename_01ab375a_uniq" UNIQUE ("content_type_id", "codename"),
    CONSTRAINT "auth_permission_content_type_id_2f476e4b_fk_django_co" FOREIGN KEY ("content_type_id") REFERENCES "public"."django_content_type"("id") DEFERRABLE INITIALLY DEFERRED
);



--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."auth_group_permissions" (
    "id" integer NOT NULL,
    "group_id" integer NOT NULL,
    "permission_id" integer NOT NULL,
    CONSTRAINT "auth_group_permissions_group_id_permission_id_0cd325b0_uniq" UNIQUE ("group_id", "permission_id"),
    CONSTRAINT "auth_group_permissions_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "auth_group_permissio_permission_id_84c5c92e_fk_auth_perm" FOREIGN KEY ("permission_id") REFERENCES "public"."auth_permission"("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "auth_group_permissions_group_id_b120cbf9_fk_auth_group_id" FOREIGN KEY ("group_id") REFERENCES "public"."auth_group"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."auth_group_permissions_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."auth_group_permissions_id_seq" OWNED BY "public"."auth_group_permissions"."id";


--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."auth_permission_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."auth_permission_id_seq" OWNED BY "public"."auth_permission"."id";


--
-- Name: auth_user_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."auth_user_groups" (
    "id" integer NOT NULL,
    "user_id" integer NOT NULL,
    "group_id" integer NOT NULL,
    CONSTRAINT "auth_user_groups_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "auth_user_groups_user_id_group_id_94350c0c_uniq" UNIQUE ("user_id", "group_id"),
    CONSTRAINT "auth_user_groups_group_id_97559544_fk_auth_group_id" FOREIGN KEY ("group_id") REFERENCES "public"."auth_group"("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "auth_user_groups_user_id_6a12ed8b_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."auth_user_groups_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."auth_user_groups_id_seq" OWNED BY "public"."auth_user_groups"."id";


--
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."auth_user_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."auth_user_id_seq" OWNED BY "public"."auth_user"."id";


--
-- Name: auth_user_user_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."auth_user_user_permissions" (
    "id" integer NOT NULL,
    "user_id" integer NOT NULL,
    "permission_id" integer NOT NULL,
    CONSTRAINT "auth_user_user_permissions_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "auth_user_user_permissions_user_id_permission_id_14a6b632_uniq" UNIQUE ("user_id", "permission_id"),
    CONSTRAINT "auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm" FOREIGN KEY ("permission_id") REFERENCES "public"."auth_permission"("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."auth_user_user_permissions_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."auth_user_user_permissions_id_seq" OWNED BY "public"."auth_user_user_permissions"."id";


--
-- Name: tab; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."tab" (
    "id" integer NOT NULL,
    "slug" character varying(50) NOT NULL,
    "name" "text" NOT NULL,
    "position" integer NOT NULL,
    "selected_step_position" integer,
    "is_deleted" boolean NOT NULL,
    "workflow_id" integer NOT NULL,
    CONSTRAINT "server_tab_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "server_tab_workflow_id_slug_95e85421_uniq" UNIQUE ("workflow_id", "slug"),
    CONSTRAINT "server_tab_workflow_id_cfd7a7d2_fk_server_workflow_id" FOREIGN KEY ("workflow_id") REFERENCES "public"."workflow"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: step; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."step" (
    "id" integer NOT NULL,
    "module_id_name" character varying(200) NOT NULL,
    "order" integer NOT NULL,
    "notes" "text",
    "stored_data_version" timestamp with time zone,
    "is_collapsed" boolean NOT NULL,
    "is_deleted" boolean NOT NULL,
    "auto_update_data" boolean NOT NULL,
    "next_update" timestamp with time zone,
    "update_interval" integer NOT NULL,
    "last_update_check" timestamp with time zone,
    "notifications" boolean NOT NULL,
    "has_unseen_notification" boolean NOT NULL,
    "cached_render_result_delta_id" integer,
    "cached_render_result_status" character varying(20),
    "cached_render_result_json" "bytea" NOT NULL,
    "cached_render_result_columns" "jsonb",
    "cached_render_result_nrows" integer,
    "is_busy" boolean NOT NULL,
    "last_relevant_delta_id" integer NOT NULL,
    "params" "jsonb" NOT NULL,
    "secrets" "jsonb" NOT NULL,
    "tab_id" integer NOT NULL,
    "file_upload_api_token" character varying(100),
    "slug" character varying(50) NOT NULL,
    "cached_render_result_errors" "jsonb" NOT NULL,
    "cached_migrated_params" "jsonb",
    "cached_migrated_params_module_version" character varying(200),
    "fetch_errors" "jsonb" NOT NULL,
    CONSTRAINT "auto_update_consistency_check" CHECK (((("next_update" IS NULL) AND ("auto_update_data" = false)) OR (("next_update" IS NOT NULL) AND ("auto_update_data" = true)))),
    CONSTRAINT "cached_migrated_params_consistency_check" CHECK (((("cached_migrated_params" IS NULL) AND ("cached_migrated_params_module_version" IS NULL)) OR (("cached_migrated_params" IS NOT NULL) AND ("cached_migrated_params_module_version" IS NOT NULL)))),
    CONSTRAINT "server_wfmodule_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "unique_wf_module_slug" UNIQUE ("tab_id", "slug"),
    CONSTRAINT "server_wfmodule_tab_id_1d1292aa_fk_server_tab_id" FOREIGN KEY ("tab_id") REFERENCES "public"."tab"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: block; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."block" (
    "id" integer NOT NULL,
    "slug" character varying(50) NOT NULL,
    "position" integer NOT NULL,
    "block_type" character varying(5) NOT NULL,
    "text_markdown" "text" NOT NULL,
    "step_id" integer,
    "tab_id" integer,
    "workflow_id" integer NOT NULL,
    CONSTRAINT "block_type_nulls_check" CHECK ((((("block_type")::"text" = 'Chart'::"text") AND ("step_id" IS NOT NULL) AND ("tab_id" IS NULL) AND ("text_markdown" = ''::"text")) OR ((("block_type")::"text" = 'Table'::"text") AND ("step_id" IS NULL) AND ("tab_id" IS NOT NULL) AND ("text_markdown" = ''::"text")) OR ((("block_type")::"text" = 'Text'::"text") AND ("step_id" IS NULL) AND ("tab_id" IS NULL) AND (NOT ("text_markdown" = ''::"text"))))),
    CONSTRAINT "block_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "unique_workflow_block_positions" UNIQUE ("workflow_id", "position"),
    CONSTRAINT "unique_workflow_block_slugs" UNIQUE ("workflow_id", "slug"),
    CONSTRAINT "block_step_id_d7168ba8_fk_step_id" FOREIGN KEY ("step_id") REFERENCES "public"."step"("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "block_tab_id_8a96da0e_fk_tab_id" FOREIGN KEY ("tab_id") REFERENCES "public"."tab"("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "block_workflow_id_10e5b1d5_fk_workflow_id" FOREIGN KEY ("workflow_id") REFERENCES "public"."workflow"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: block_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."block_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: block_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."block_id_seq" OWNED BY "public"."block"."id";


--
-- Name: cjworkbench_userprofile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."cjworkbench_userprofile" (
    "id" integer NOT NULL,
    "get_newsletter" boolean NOT NULL,
    "user_id" integer NOT NULL,
    "max_fetches_per_day" integer NOT NULL,
    "locale_id" character varying(5) NOT NULL,
    "stripe_customer_id" character varying(50),
    CONSTRAINT "cjworkbench_userprofile_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "cjworkbench_userprofile_user_id_key" UNIQUE ("user_id"),
    CONSTRAINT "cjworkbench_userprofile_user_id_8c5b5dbd_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: cjworkbench_userprofile_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."cjworkbench_userprofile_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cjworkbench_userprofile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."cjworkbench_userprofile_id_seq" OWNED BY "public"."cjworkbench_userprofile"."id";


--
-- Name: delta; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."delta" (
    "id" integer NOT NULL,
    "datetime" timestamp with time zone NOT NULL,
    "prev_delta_id" integer,
    "workflow_id" integer NOT NULL,
    "step_id" integer,
    "step_delta_ids" integer[] NOT NULL,
    "tab_id" integer,
    "values_for_backward" "jsonb" NOT NULL,
    "values_for_forward" "jsonb" NOT NULL,
    "command_name" character varying(18) NOT NULL,
    "last_applied_at" timestamp with time zone NOT NULL,
    CONSTRAINT "delta_command_name_valid" CHECK ((("command_name")::"text" = ANY ((ARRAY['AddBlock'::character varying, 'AddStep'::character varying, 'AddTab'::character varying, 'DeleteBlock'::character varying, 'DeleteStep'::character varying, 'DeleteTab'::character varying, 'DuplicateTab'::character varying, 'InitWorkflow'::character varying, 'ReorderBlocks'::character varying, 'ReorderSteps'::character varying, 'ReorderTabs'::character varying, 'SetBlockMarkdown'::character varying, 'SetStepDataVersion'::character varying, 'SetStepNote'::character varying, 'SetStepParams'::character varying, 'SetTabName'::character varying, 'SetWorkflowTitle'::character varying])::"text"[]))),
    CONSTRAINT "server_delta_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "server_delta_prev_delta_id_key" UNIQUE ("prev_delta_id"),
    CONSTRAINT "delta_step_id_fd7f5956_fk_step_id" FOREIGN KEY ("step_id") REFERENCES "public"."step"("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "delta_tab_id_7e257bc1_fk_tab_id" FOREIGN KEY ("tab_id") REFERENCES "public"."tab"("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "server_delta_prev_delta_id_c5d166bf_fk_server_delta_id" FOREIGN KEY ("prev_delta_id") REFERENCES "public"."delta"("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "server_delta_workflow_id_166b01d4_fk_server_workflow_id" FOREIGN KEY ("workflow_id") REFERENCES "public"."workflow"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."django_admin_log" (
    "id" integer NOT NULL,
    "action_time" timestamp with time zone NOT NULL,
    "object_id" "text",
    "object_repr" character varying(200) NOT NULL,
    "action_flag" smallint NOT NULL,
    "change_message" "text" NOT NULL,
    "content_type_id" integer,
    "user_id" integer NOT NULL,
    CONSTRAINT "django_admin_log_action_flag_check" CHECK (("action_flag" >= 0)),
    CONSTRAINT "django_admin_log_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "django_admin_log_content_type_id_c4bce8eb_fk_django_co" FOREIGN KEY ("content_type_id") REFERENCES "public"."django_content_type"("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "django_admin_log_user_id_c564eba6_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."django_admin_log_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."django_admin_log_id_seq" OWNED BY "public"."django_admin_log"."id";


--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."django_content_type_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: django_content_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."django_content_type_id_seq" OWNED BY "public"."django_content_type"."id";


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."django_migrations" (
    "id" integer NOT NULL,
    "app" character varying(255) NOT NULL,
    "name" character varying(255) NOT NULL,
    "applied" timestamp with time zone NOT NULL,
    CONSTRAINT "django_migrations_pkey" PRIMARY KEY ("id")
);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."django_migrations_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: django_migrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."django_migrations_id_seq" OWNED BY "public"."django_migrations"."id";


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."django_session" (
    "session_key" character varying(40) NOT NULL,
    "session_data" "text" NOT NULL,
    "expire_date" timestamp with time zone NOT NULL,
    CONSTRAINT "django_session_pkey" PRIMARY KEY ("session_key")
);


--
-- Name: django_site; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."django_site" (
    "id" integer NOT NULL,
    "domain" character varying(100) NOT NULL,
    "name" character varying(50) NOT NULL,
    CONSTRAINT "django_site_domain_a2e37b91_uniq" UNIQUE ("domain"),
    CONSTRAINT "django_site_pkey" PRIMARY KEY ("id")
);


--
-- Name: django_site_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."django_site_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: django_site_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."django_site_id_seq" OWNED BY "public"."django_site"."id";


--
-- Name: module_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."module_version" (
    "id" integer NOT NULL,
    "id_name" character varying(200) NOT NULL,
    "source_version_hash" character varying(200) NOT NULL,
    "last_update_time" timestamp with time zone NOT NULL,
    "spec" "jsonb" NOT NULL,
    "js_module" "text" NOT NULL,
    CONSTRAINT "server_moduleversion_id_name_last_update_time_fad49fda_uniq" UNIQUE ("id_name", "last_update_time"),
    CONSTRAINT "server_moduleversion_pkey" PRIMARY KEY ("id")
);


--
-- Name: plan_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."plan_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: plan_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."plan_id_seq" OWNED BY "public"."price"."id";


--
-- Name: product_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."product_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: product_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."product_id_seq" OWNED BY "public"."product"."id";


--
-- Name: server_aclentry_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."server_aclentry_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: server_aclentry_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."server_aclentry_id_seq" OWNED BY "public"."acl_entry"."id";


--
-- Name: server_delta_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."server_delta_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: server_delta_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."server_delta_id_seq" OWNED BY "public"."delta"."id";


--
-- Name: server_moduleversion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."server_moduleversion_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: server_moduleversion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."server_moduleversion_id_seq" OWNED BY "public"."module_version"."id";


--
-- Name: stored_object; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."stored_object" (
    "id" integer NOT NULL,
    "key" character varying(255) NOT NULL,
    "stored_at" timestamp with time zone NOT NULL,
    "hash" character varying(32) NOT NULL,
    "size" integer NOT NULL,
    "read" boolean NOT NULL,
    "step_id" integer NOT NULL,
    CONSTRAINT "server_storedobject_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "server_storedobject_step_id_7f16e7aa_fk_server_wfmodule_id" FOREIGN KEY ("step_id") REFERENCES "public"."step"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: server_storedobject_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."server_storedobject_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: server_storedobject_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."server_storedobject_id_seq" OWNED BY "public"."stored_object"."id";


--
-- Name: server_tab_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."server_tab_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: server_tab_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."server_tab_id_seq" OWNED BY "public"."tab"."id";


--
-- Name: uploaded_file; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."uploaded_file" (
    "id" integer NOT NULL,
    "name" character varying(255) NOT NULL,
    "size" integer NOT NULL,
    "uuid" character varying(255) NOT NULL,
    "key" character varying(255) NOT NULL,
    "step_id" integer NOT NULL,
    "created_at" timestamp with time zone,
    CONSTRAINT "server_uploadedfile_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "server_uploadedfile_step_id_abfcc900_fk_server_wfmodule_id" FOREIGN KEY ("step_id") REFERENCES "public"."step"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: server_uploadedfile_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."server_uploadedfile_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: server_uploadedfile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."server_uploadedfile_id_seq" OWNED BY "public"."uploaded_file"."id";


--
-- Name: server_wfmodule_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."server_wfmodule_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: server_wfmodule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."server_wfmodule_id_seq" OWNED BY "public"."step"."id";


--
-- Name: server_workflow_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."server_workflow_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: server_workflow_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."server_workflow_id_seq" OWNED BY "public"."workflow"."id";


--
-- Name: socialaccount_socialaccount; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."socialaccount_socialaccount" (
    "id" integer NOT NULL,
    "provider" character varying(30) NOT NULL,
    "uid" character varying(191) NOT NULL,
    "last_login" timestamp with time zone NOT NULL,
    "date_joined" timestamp with time zone NOT NULL,
    "extra_data" "text" NOT NULL,
    "user_id" integer NOT NULL,
    CONSTRAINT "socialaccount_socialaccount_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "socialaccount_socialaccount_provider_uid_fc810c6e_uniq" UNIQUE ("provider", "uid"),
    CONSTRAINT "socialaccount_socialaccount_user_id_8146e70c_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: socialaccount_socialaccount_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."socialaccount_socialaccount_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: socialaccount_socialaccount_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."socialaccount_socialaccount_id_seq" OWNED BY "public"."socialaccount_socialaccount"."id";


--
-- Name: socialaccount_socialapp; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."socialaccount_socialapp" (
    "id" integer NOT NULL,
    "provider" character varying(30) NOT NULL,
    "name" character varying(40) NOT NULL,
    "client_id" character varying(191) NOT NULL,
    "secret" character varying(191) NOT NULL,
    "key" character varying(191) NOT NULL,
    CONSTRAINT "socialaccount_socialapp_pkey" PRIMARY KEY ("id")
);


--
-- Name: socialaccount_socialapp_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."socialaccount_socialapp_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: socialaccount_socialapp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."socialaccount_socialapp_id_seq" OWNED BY "public"."socialaccount_socialapp"."id";


--
-- Name: socialaccount_socialapp_sites; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."socialaccount_socialapp_sites" (
    "id" integer NOT NULL,
    "socialapp_id" integer NOT NULL,
    "site_id" integer NOT NULL,
    CONSTRAINT "socialaccount_socialapp__socialapp_id_site_id_71a9a768_uniq" UNIQUE ("socialapp_id", "site_id"),
    CONSTRAINT "socialaccount_socialapp_sites_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "socialaccount_social_site_id_2579dee5_fk_django_si" FOREIGN KEY ("site_id") REFERENCES "public"."django_site"("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "socialaccount_social_socialapp_id_97fb6e7d_fk_socialacc" FOREIGN KEY ("socialapp_id") REFERENCES "public"."socialaccount_socialapp"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: socialaccount_socialapp_sites_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."socialaccount_socialapp_sites_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: socialaccount_socialapp_sites_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."socialaccount_socialapp_sites_id_seq" OWNED BY "public"."socialaccount_socialapp_sites"."id";


--
-- Name: socialaccount_socialtoken; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."socialaccount_socialtoken" (
    "id" integer NOT NULL,
    "token" "text" NOT NULL,
    "token_secret" "text" NOT NULL,
    "expires_at" timestamp with time zone,
    "account_id" integer NOT NULL,
    "app_id" integer NOT NULL,
    CONSTRAINT "socialaccount_socialtoken_app_id_account_id_fca4e0ac_uniq" UNIQUE ("app_id", "account_id"),
    CONSTRAINT "socialaccount_socialtoken_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "socialaccount_social_account_id_951f210e_fk_socialacc" FOREIGN KEY ("account_id") REFERENCES "public"."socialaccount_socialaccount"("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "socialaccount_social_app_id_636a42d7_fk_socialacc" FOREIGN KEY ("app_id") REFERENCES "public"."socialaccount_socialapp"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: socialaccount_socialtoken_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."socialaccount_socialtoken_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: socialaccount_socialtoken_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."socialaccount_socialtoken_id_seq" OWNED BY "public"."socialaccount_socialtoken"."id";


--
-- Name: subscription; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS "public"."subscription" (
    "id" integer NOT NULL,
    "stripe_subscription_id" character varying(50) NOT NULL,
    "stripe_status" character varying(18) NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "renewed_at" timestamp with time zone NOT NULL,
    "price_id" integer NOT NULL,
    "user_id" integer NOT NULL,
    CONSTRAINT "subscription_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "subscription_stripe_subscription_id_key" UNIQUE ("stripe_subscription_id"),
    CONSTRAINT "subscription_price_id_be60d2cf_fk_price_id" FOREIGN KEY ("price_id") REFERENCES "public"."price"("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "subscription_user_id_856cd8e2_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);


--
-- Name: subscription_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS "public"."subscription_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: subscription_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."subscription_id_seq" OWNED BY "public"."subscription"."id";


--
-- Name: account_emailaddress id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."account_emailaddress" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."account_emailaddress_id_seq"'::"regclass");


--
-- Name: account_emailconfirmation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."account_emailconfirmation" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."account_emailconfirmation_id_seq"'::"regclass");


--
-- Name: acl_entry id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."acl_entry" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."server_aclentry_id_seq"'::"regclass");


--
-- Name: auth_group id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."auth_group" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."auth_group_id_seq"'::"regclass");


--
-- Name: auth_group_permissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."auth_group_permissions" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."auth_group_permissions_id_seq"'::"regclass");


--
-- Name: auth_permission id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."auth_permission" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."auth_permission_id_seq"'::"regclass");


--
-- Name: auth_user id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."auth_user" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."auth_user_id_seq"'::"regclass");


--
-- Name: auth_user_groups id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."auth_user_groups" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."auth_user_groups_id_seq"'::"regclass");


--
-- Name: auth_user_user_permissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."auth_user_user_permissions" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."auth_user_user_permissions_id_seq"'::"regclass");


--
-- Name: block id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."block" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."block_id_seq"'::"regclass");


--
-- Name: cjworkbench_userprofile id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."cjworkbench_userprofile" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."cjworkbench_userprofile_id_seq"'::"regclass");


--
-- Name: delta id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."delta" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."server_delta_id_seq"'::"regclass");


--
-- Name: django_admin_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."django_admin_log" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."django_admin_log_id_seq"'::"regclass");


--
-- Name: django_content_type id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."django_content_type" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."django_content_type_id_seq"'::"regclass");


--
-- Name: django_migrations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."django_migrations" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."django_migrations_id_seq"'::"regclass");


--
-- Name: django_site id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."django_site" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."django_site_id_seq"'::"regclass");


--
-- Name: module_version id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."module_version" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."server_moduleversion_id_seq"'::"regclass");


--
-- Name: price id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."price" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."plan_id_seq"'::"regclass");


--
-- Name: product id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."product" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."product_id_seq"'::"regclass");


--
-- Name: socialaccount_socialaccount id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."socialaccount_socialaccount" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."socialaccount_socialaccount_id_seq"'::"regclass");


--
-- Name: socialaccount_socialapp id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."socialaccount_socialapp" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."socialaccount_socialapp_id_seq"'::"regclass");


--
-- Name: socialaccount_socialapp_sites id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."socialaccount_socialapp_sites" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."socialaccount_socialapp_sites_id_seq"'::"regclass");


--
-- Name: socialaccount_socialtoken id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."socialaccount_socialtoken" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."socialaccount_socialtoken_id_seq"'::"regclass");


--
-- Name: step id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."step" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."server_wfmodule_id_seq"'::"regclass");


--
-- Name: stored_object id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."stored_object" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."server_storedobject_id_seq"'::"regclass");


--
-- Name: subscription id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."subscription" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."subscription_id_seq"'::"regclass");


--
-- Name: tab id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."tab" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."server_tab_id_seq"'::"regclass");


--
-- Name: uploaded_file id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."uploaded_file" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."server_uploadedfile_id_seq"'::"regclass");


--
-- Name: workflow id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."workflow" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."server_workflow_id_seq"'::"regclass");


--
-- Name: account_emailaddress_email_03be32b2_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "account_emailaddress_email_03be32b2_like" ON "public"."account_emailaddress" USING "btree" ("email" "varchar_pattern_ops");


--
-- Name: account_emailaddress_user_id_2c513194; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "account_emailaddress_user_id_2c513194" ON "public"."account_emailaddress" USING "btree" ("user_id");


--
-- Name: account_emailconfirmation_email_address_id_5b7f8c58; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "account_emailconfirmation_email_address_id_5b7f8c58" ON "public"."account_emailconfirmation" USING "btree" ("email_address_id");


--
-- Name: account_emailconfirmation_key_f43612bd_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "account_emailconfirmation_key_f43612bd_like" ON "public"."account_emailconfirmation" USING "btree" ("key" "varchar_pattern_ops");


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "auth_group_name_a6ea08ec_like" ON "public"."auth_group" USING "btree" ("name" "varchar_pattern_ops");


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "auth_group_permissions_group_id_b120cbf9" ON "public"."auth_group_permissions" USING "btree" ("group_id");


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "auth_group_permissions_permission_id_84c5c92e" ON "public"."auth_group_permissions" USING "btree" ("permission_id");


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "auth_permission_content_type_id_2f476e4b" ON "public"."auth_permission" USING "btree" ("content_type_id");


--
-- Name: auth_user_groups_group_id_97559544; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "auth_user_groups_group_id_97559544" ON "public"."auth_user_groups" USING "btree" ("group_id");


--
-- Name: auth_user_groups_user_id_6a12ed8b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "auth_user_groups_user_id_6a12ed8b" ON "public"."auth_user_groups" USING "btree" ("user_id");


--
-- Name: auth_user_user_permissions_permission_id_1fbb5f2c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "auth_user_user_permissions_permission_id_1fbb5f2c" ON "public"."auth_user_user_permissions" USING "btree" ("permission_id");


--
-- Name: auth_user_user_permissions_user_id_a95ead1b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "auth_user_user_permissions_user_id_a95ead1b" ON "public"."auth_user_user_permissions" USING "btree" ("user_id");


--
-- Name: auth_user_username_6821ab7c_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "auth_user_username_6821ab7c_like" ON "public"."auth_user" USING "btree" ("username" "varchar_pattern_ops");


--
-- Name: block_slug_b527bbdc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "block_slug_b527bbdc" ON "public"."block" USING "btree" ("slug");


--
-- Name: block_slug_b527bbdc_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "block_slug_b527bbdc_like" ON "public"."block" USING "btree" ("slug" "varchar_pattern_ops");


--
-- Name: block_step_id_d7168ba8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "block_step_id_d7168ba8" ON "public"."block" USING "btree" ("step_id");


--
-- Name: block_tab_id_8a96da0e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "block_tab_id_8a96da0e" ON "public"."block" USING "btree" ("tab_id");


--
-- Name: block_workflow_id_10e5b1d5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "block_workflow_id_10e5b1d5" ON "public"."block" USING "btree" ("workflow_id");


--
-- Name: cjworkbench_userprofile_stripe_customer_id_7e5ae024; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "cjworkbench_userprofile_stripe_customer_id_7e5ae024" ON "public"."cjworkbench_userprofile" USING "btree" ("stripe_customer_id");


--
-- Name: cjworkbench_userprofile_stripe_customer_id_7e5ae024_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "cjworkbench_userprofile_stripe_customer_id_7e5ae024_like" ON "public"."cjworkbench_userprofile" USING "btree" ("stripe_customer_id" "varchar_pattern_ops");


--
-- Name: delta_migrate_step_id_47bd3d50; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "delta_migrate_step_id_47bd3d50" ON "public"."delta" USING "btree" ("step_id");


--
-- Name: delta_migrate_tab_id_353938fc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "delta_migrate_tab_id_353938fc" ON "public"."delta" USING "btree" ("tab_id");


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "django_admin_log_content_type_id_c4bce8eb" ON "public"."django_admin_log" USING "btree" ("content_type_id");


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "django_admin_log_user_id_c564eba6" ON "public"."django_admin_log" USING "btree" ("user_id");


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "django_session_expire_date_a5c62663" ON "public"."django_session" USING "btree" ("expire_date");


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "django_session_session_key_c0390e0f_like" ON "public"."django_session" USING "btree" ("session_key" "varchar_pattern_ops");


--
-- Name: django_site_domain_a2e37b91_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "django_site_domain_a2e37b91_like" ON "public"."django_site" USING "btree" ("domain" "varchar_pattern_ops");


--
-- Name: index_delta_for_stale_scan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "index_delta_for_stale_scan" ON "public"."delta" USING "btree" ("workflow_id", "last_applied_at");


--
-- Name: pending_update_queue; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "pending_update_queue" ON "public"."step" USING "btree" ("next_update") WHERE (("is_deleted" = false) AND ("next_update" IS NOT NULL));


--
-- Name: plan_stripe_price_id_6e31f30a_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "plan_stripe_price_id_6e31f30a_like" ON "public"."price" USING "btree" ("stripe_price_id" "varchar_pattern_ops");


--
-- Name: price_product_id_4d9c683d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "price_product_id_4d9c683d" ON "public"."price" USING "btree" ("product_id");


--
-- Name: product_stripe_product_id_44bb8823; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "product_stripe_product_id_44bb8823" ON "public"."product" USING "btree" ("stripe_product_id");


--
-- Name: product_stripe_product_id_44bb8823_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "product_stripe_product_id_44bb8823_like" ON "public"."product" USING "btree" ("stripe_product_id" "varchar_pattern_ops");


--
-- Name: server_aclentry_email_c485566c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "server_aclentry_email_c485566c" ON "public"."acl_entry" USING "btree" ("email");


--
-- Name: server_aclentry_email_c485566c_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "server_aclentry_email_c485566c_like" ON "public"."acl_entry" USING "btree" ("email" "varchar_pattern_ops");


--
-- Name: server_aclentry_workflow_id_c722e228; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "server_aclentry_workflow_id_c722e228" ON "public"."acl_entry" USING "btree" ("workflow_id");


--
-- Name: server_delta_workflow_id_166b01d4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "server_delta_workflow_id_166b01d4" ON "public"."delta" USING "btree" ("workflow_id");


--
-- Name: server_storedobject_wf_module_id_69836ada; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "server_storedobject_wf_module_id_69836ada" ON "public"."stored_object" USING "btree" ("step_id");


--
-- Name: server_tab_workflow_id_cfd7a7d2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "server_tab_workflow_id_cfd7a7d2" ON "public"."tab" USING "btree" ("workflow_id");


--
-- Name: server_uploadedfile_wf_module_id_caa988b6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "server_uploadedfile_wf_module_id_caa988b6" ON "public"."uploaded_file" USING "btree" ("step_id");


--
-- Name: server_wfmodule_slug_e12bb647; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "server_wfmodule_slug_e12bb647" ON "public"."step" USING "btree" ("slug");


--
-- Name: server_wfmodule_slug_e12bb647_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "server_wfmodule_slug_e12bb647_like" ON "public"."step" USING "btree" ("slug" "varchar_pattern_ops");


--
-- Name: server_wfmodule_tab_id_1d1292aa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "server_wfmodule_tab_id_1d1292aa" ON "public"."step" USING "btree" ("tab_id");


--
-- Name: server_workflow_last_delta_id_c5adfe9b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "server_workflow_last_delta_id_c5adfe9b" ON "public"."workflow" USING "btree" ("last_delta_id");


--
-- Name: server_workflow_owner_id_aa1f16c9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "server_workflow_owner_id_aa1f16c9" ON "public"."workflow" USING "btree" ("owner_id");


--
-- Name: socialaccount_socialaccount_user_id_8146e70c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "socialaccount_socialaccount_user_id_8146e70c" ON "public"."socialaccount_socialaccount" USING "btree" ("user_id");


--
-- Name: socialaccount_socialapp_sites_site_id_2579dee5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "socialaccount_socialapp_sites_site_id_2579dee5" ON "public"."socialaccount_socialapp_sites" USING "btree" ("site_id");


--
-- Name: socialaccount_socialapp_sites_socialapp_id_97fb6e7d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "socialaccount_socialapp_sites_socialapp_id_97fb6e7d" ON "public"."socialaccount_socialapp_sites" USING "btree" ("socialapp_id");


--
-- Name: socialaccount_socialtoken_account_id_951f210e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "socialaccount_socialtoken_account_id_951f210e" ON "public"."socialaccount_socialtoken" USING "btree" ("account_id");


--
-- Name: socialaccount_socialtoken_app_id_636a42d7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "socialaccount_socialtoken_app_id_636a42d7" ON "public"."socialaccount_socialtoken" USING "btree" ("app_id");


--
-- Name: subscription_plan_id_967284a5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "subscription_plan_id_967284a5" ON "public"."subscription" USING "btree" ("price_id");


--
-- Name: subscription_stripe_subscription_id_572aef84_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "subscription_stripe_subscription_id_572aef84_like" ON "public"."subscription" USING "btree" ("stripe_subscription_id" "varchar_pattern_ops");


--
-- Name: subscription_user_id_856cd8e2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS "subscription_user_id_856cd8e2" ON "public"."subscription" USING "btree" ("user_id");


--
-- Name: unique_workflow_copy_by_session; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX IF NOT EXISTS "unique_workflow_copy_by_session" ON "public"."workflow" USING "btree" ("anonymous_owner_session_key", "original_workflow_id") WHERE (("anonymous_owner_session_key" IS NOT NULL) AND ("original_workflow_id" IS NOT NULL));


INSERT INTO django_site (id, domain, name)
VALUES (1, 'app.workbenchdata.com', 'Workbench')
ON CONFLICT (id)
DO UPDATE SET domain = 'app.workbenchdata.com', name = 'Workbench';
