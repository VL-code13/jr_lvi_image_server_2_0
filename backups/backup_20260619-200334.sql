--
-- PostgreSQL database dump
--

\restrict eqNdPAcTWPGe6aa8U9KzQfcKqcW1Thsd1JD0pnDf0D94ihW8yBvOEsEjd4jRlqb

-- Dumped from database version 15.18 (Debian 15.18-1.pgdg13+1)
-- Dumped by pg_dump version 15.18 (Debian 15.18-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: images; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.images (
    id integer NOT NULL,
    filename character varying(255) NOT NULL,
    original_filename character varying(255) NOT NULL,
    size integer NOT NULL,
    upload_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    file_type character varying(10) NOT NULL
);


ALTER TABLE public.images OWNER TO postgres;

--
-- Name: images_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.images_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.images_id_seq OWNER TO postgres;

--
-- Name: images_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.images_id_seq OWNED BY public.images.id;


--
-- Name: images id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.images ALTER COLUMN id SET DEFAULT nextval('public.images_id_seq'::regclass);


--
-- Data for Name: images; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.images (id, filename, original_filename, size, upload_time, file_type) FROM stdin;
1	fcefea25608546e584b97f50d923b255.png	docker_nonstop.png	229151	2026-06-13 08:10:06.527653	png
2	f1fd02c806b44ffa8827ef79a828f049.png	Screenshot from 2026-04-10 21-24-06.png	529040	2026-06-13 08:10:28.946325	png
3	7106ef3dc4004e22a1cfc45c29030016.png	docker_nonstop.png	229151	2026-06-13 08:12:24.724278	png
4	3eaedddfcb2b4e78ae0647527d79b266.png	docker_nonstop.png	229151	2026-06-13 08:12:28.56262	png
5	41998b7521b349c692a984f91e95a2e8.png	docker_nonstop.png	229151	2026-06-13 08:12:36.911379	png
6	22b6010c77444fc5988248a619694dd4.png	docker_nonstop.png	229151	2026-06-13 08:12:42.434246	png
7	ee30d04798d041d9b8992d9c97fcf15f.png	docker_nonstop.png	229151	2026-06-13 08:12:49.819625	png
8	ec2bfd122cf6453588a07e3a0e65f550.png	docker_nonstop.png	229151	2026-06-13 08:13:01.572552	png
9	830fa0f8b2ed4fda85a3de69e1d6ffeb.png	docker_nonstop.png	229151	2026-06-13 08:13:06.270195	png
10	72d66a252c5645f2ac442e5c385ba572.png	docker_nonstop.png	229151	2026-06-13 08:13:10.87726	png
11	3668ee2fec304c8b84659dc8a686c876.png	docker_nonstop.png	229151	2026-06-13 08:13:15.582588	png
12	97c503207be7481696023f103f64801f.png	docker_nonstop.png	229151	2026-06-13 08:13:19.883267	png
13	c385e0ea3ea64059bcd609e53f3c32ea.png	docker_nonstop.png	229151	2026-06-19 16:56:12.363167	png
\.


--
-- Name: images_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.images_id_seq', 13, true);


--
-- Name: images images_filename_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_filename_key UNIQUE (filename);


--
-- Name: images images_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict eqNdPAcTWPGe6aa8U9KzQfcKqcW1Thsd1JD0pnDf0D94ihW8yBvOEsEjd4jRlqb

