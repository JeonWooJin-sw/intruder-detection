package com.example.photoviewer;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

/** 서버 /api_root/archive/ 의 하루치 감지 기록 (편의 기능 2: 감지 기록 아카이브) */
public class ArchiveDay {

    public final String date;      // "2026-11-10"
    public final int total;        // 그날 YOLO가 올린 글 수
    public final List<String> titles = new ArrayList<>();    // 물체 이름 (많은 순)
    public final List<Integer> counts = new ArrayList<>();

    public ArchiveDay(String date, int total) {
        this.date = date;
        this.total = total;
    }

    public static ArchiveDay fromJson(JSONObject json) throws JSONException {
        ArchiveDay day = new ArchiveDay(json.getString("date"), json.getInt("total"));
        JSONArray objects = json.getJSONArray("objects");
        for (int i = 0; i < objects.length(); i++) {
            JSONObject o = objects.getJSONObject(i);
            day.titles.add(o.getString("title"));
            day.counts.add(o.getInt("count"));
        }
        return day;
    }

    /** "cell phone 5 · book 1 · cup 1" */
    public String summary() {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < titles.size(); i++) {
            if (i > 0) sb.append(" · ");
            sb.append(titles.get(i)).append(' ').append(counts.get(i));
        }
        return sb.toString();
    }
}
